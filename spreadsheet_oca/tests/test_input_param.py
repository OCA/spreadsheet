# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Tests for named input parameters.

Covers:
  - cell_ref.py helper functions (pure logic, no DB).
  - spreadsheet.input_param model creation, constraints, and sync.
  - _apply_param_substitution domain helper.
  - Smart button count and action.
  - Full refresh-cycle integration (param sync + domain substitution).
  - Controller endpoint logic (model-level).
"""

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger

from ..models.cell_ref import (
    parse_cell_key,
    parse_cell_ref,
    read_cell_value,
    write_cell_content,
)
from ..models.spreadsheet_refresh_schedule import _apply_param_substitution


class TestCellRefHelpers(TransactionCase):
    """Unit tests for cell_ref.py — pure logic, no DB required."""

    # ── parse_cell_ref ────────────────────────────────────────────────────────

    def test_parse_cell_ref_simple(self):
        self.assertEqual(parse_cell_ref("A1"), (0, 0))
        self.assertEqual(parse_cell_ref("B3"), (1, 2))
        self.assertEqual(parse_cell_ref("Z1"), (25, 0))

    def test_parse_cell_ref_multi_letter(self):
        col, row = parse_cell_ref("AA1")
        self.assertEqual(col, 26)
        self.assertEqual(row, 0)
        col2, row2 = parse_cell_ref("AB12")
        self.assertEqual(col2, 27)
        self.assertEqual(row2, 11)

    def test_parse_cell_ref_invalid(self):
        self.assertEqual(parse_cell_ref(""), (None, None))
        self.assertEqual(parse_cell_ref("A0"), (None, None))  # zero row forbidden
        self.assertEqual(parse_cell_ref("12"), (None, None))  # no letters
        self.assertEqual(parse_cell_ref("ZZZ"), (None, None))  # no row number

    def test_parse_cell_ref_case_insensitive(self):
        self.assertEqual(parse_cell_ref("b3"), parse_cell_ref("B3"))

    # ── parse_cell_key ────────────────────────────────────────────────────────

    def test_parse_cell_key_bare(self):
        sheet, col, row = parse_cell_key("B3")
        self.assertIsNone(sheet)
        self.assertEqual(col, 1)
        self.assertEqual(row, 2)

    def test_parse_cell_key_with_sheet(self):
        sheet, col, row = parse_cell_key("Sheet1!B3")
        self.assertEqual(sheet, "Sheet1")
        self.assertEqual(col, 1)
        self.assertEqual(row, 2)

    def test_parse_cell_key_invalid(self):
        sheet, col, row = parse_cell_key("ZZZ")
        self.assertIsNone(col)

    # ── read_cell_value ───────────────────────────────────────────────────────

    def _make_raw(self, row, col, content=None, value=None):
        cell = {}
        if content is not None:
            cell["content"] = content
        if value is not None:
            cell["value"] = value
        # Convert 0-based (col, row) to "A1" format cell address
        col_str = chr(ord("A") + col)
        cell_addr = f"{col_str}{row + 1}"
        return {
            "sheets": [
                {
                    "id": "s1",
                    "name": "Sheet1",
                    "cells": {cell_addr: cell},
                }
            ]
        }

    def test_read_cell_value_numeric(self):
        raw = self._make_raw(2, 1, content="42")  # B3
        val = read_cell_value(raw, "B3")
        self.assertEqual(val, "42")

    def test_read_cell_value_uses_evaluated_value(self):
        raw = self._make_raw(2, 1, content="=1+1", value=2)
        val = read_cell_value(raw, "B3")
        self.assertEqual(val, 2)

    def test_read_cell_value_string(self):
        raw = self._make_raw(0, 0, content="hello")  # A1
        val = read_cell_value(raw, "A1")
        self.assertEqual(val, "hello")

    def test_read_cell_value_missing(self):
        raw = {"sheets": [{"id": "s1", "name": "Sheet1", "cells": {}}]}
        val = read_cell_value(raw, "B3")
        self.assertIsNone(val)

    def test_read_cell_value_empty_raw(self):
        self.assertIsNone(read_cell_value({}, "B3"))
        self.assertIsNone(read_cell_value(None, "B3"))

    # ── write_cell_content ────────────────────────────────────────────────────

    def test_write_cell_content(self):
        raw = {"sheets": [{"id": "s1", "name": "Sheet1", "cells": {}}]}
        result = write_cell_content(raw, "B3", "hello")
        cell = result["sheets"][0]["cells"]["B3"]
        self.assertEqual(cell["content"], "hello")

    def test_write_cell_content_creates_nested_dicts(self):
        raw = {"sheets": [{"id": "s1", "name": "Sheet1"}]}
        result = write_cell_content(raw, "A1", 99)
        self.assertIn("cells", result["sheets"][0])


class TestInputParam(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spreadsheet = cls.env["spreadsheet.spreadsheet"].create(
            {"name": "Input Param Test Spreadsheet"}
        )
        # Minimal spreadsheet raw with a known cell value at B3.
        cls.raw_with_b3 = {
            "version": 1,
            "sheets": [
                {
                    "id": "s1",
                    "name": "Sheet1",
                    "cells": {
                        "B3": {"content": "2026-01-01"},
                    },
                }
            ],
        }

    def _make_param(self, **kwargs):
        defaults = {
            "name": "start_date",
            "spreadsheet_id": self.spreadsheet.id,
            "cell_ref": "B3",
        }
        defaults.update(kwargs)
        return self.env["spreadsheet.input_param"].create(defaults)

    # ── Basic creation ────────────────────────────────────────────────────────

    def test_create_param(self):
        p = self._make_param()
        self.assertEqual(p.name, "start_date")
        self.assertEqual(p.spreadsheet_id, self.spreadsheet)
        self.assertEqual(p.cell_ref, "B3")
        self.assertTrue(p.active)
        self.assertFalse(p.current_value)
        self.assertFalse(p.last_synced)

    # ── Constraint: cell_ref ─────────────────────────────────────────────────

    def test_invalid_cell_ref_raises(self):
        with self.assertRaises(ValidationError):
            self._make_param(cell_ref="ZZZ")  # letters only, no row number

    def test_valid_qualified_cell_ref(self):
        p = self._make_param(name="q_ref", cell_ref="Assumptions!C5")
        self.assertEqual(p.cell_ref, "Assumptions!C5")

    # ── Constraint: name ─────────────────────────────────────────────────────

    def test_invalid_name_raises_uppercase(self):
        with self.assertRaises(ValidationError):
            self._make_param(name="StartDate")  # uppercase forbidden

    def test_invalid_name_raises_spaces(self):
        with self.assertRaises(ValidationError):
            self._make_param(name="start date")  # spaces forbidden

    def test_invalid_name_raises_leading_digit(self):
        with self.assertRaises(ValidationError):
            self._make_param(name="1param")  # must start with letter

    # ── Constraint: unique name per spreadsheet ───────────────────────────────

    @mute_logger("odoo.sql_db")
    def test_duplicate_name_raises(self):
        self._make_param(name="dup_param")
        # SQL UNIQUE constraint propagates as psycopg2.errors.UniqueViolation
        # (IntegrityError subclass).  Catch broadly to stay decoupled from
        # psycopg2 internals and compatible across Odoo versions.
        with self.assertRaises(Exception):  # noqa: B017
            self._make_param(name="dup_param")

    # ── Sync from spreadsheet ─────────────────────────────────────────────────

    def test_sync_reads_cell(self):
        self.spreadsheet.write({"spreadsheet_raw": self.raw_with_b3})
        p = self._make_param(name="sd")
        p._sync_from_spreadsheet()
        self.assertEqual(p.current_value, "2026-01-01")

    def test_sync_updates_last_synced(self):
        self.spreadsheet.write({"spreadsheet_raw": self.raw_with_b3})
        p = self._make_param(name="sd2")
        self.assertFalse(p.last_synced)
        p._sync_from_spreadsheet()
        self.assertTrue(p.last_synced)

    def test_sync_missing_cell_no_error(self):
        """Syncing a cell that doesn't exist: no error, current_value stays None."""
        self.spreadsheet.write(
            {
                "spreadsheet_raw": {
                    "sheets": [{"id": "s1", "name": "Sheet1", "cells": {}}]
                }
            }
        )
        p = self._make_param(name="sd3", cell_ref="Z99")
        p._sync_from_spreadsheet()
        self.assertFalse(p.current_value)
        self.assertTrue(p.last_synced)

    def test_action_sync_now(self):
        """action_sync_now() is a thin wrapper that calls _sync_from_spreadsheet."""
        self.spreadsheet.write({"spreadsheet_raw": self.raw_with_b3})
        p = self._make_param(name="sd_action")
        p.action_sync_now()
        self.assertEqual(p.current_value, "2026-01-01")

    def test_sync_all_for_spreadsheet(self):
        """_sync_all_for_spreadsheet syncs all active params for a given spreadsheet."""
        self.spreadsheet.write({"spreadsheet_raw": self.raw_with_b3})
        p1 = self._make_param(name="sa_p1")
        p2 = self._make_param(name="sa_p2", cell_ref="B3")
        p3 = self._make_param(
            name="sa_p3", active=False
        )  # archived — should be skipped
        self.env["spreadsheet.input_param"]._sync_all_for_spreadsheet(
            self.spreadsheet.id
        )
        p1.invalidate_recordset()
        p2.invalidate_recordset()
        p3.invalidate_recordset()
        self.assertEqual(p1.current_value, "2026-01-01")
        self.assertEqual(p2.current_value, "2026-01-01")
        self.assertFalse(p3.current_value)  # archived param not synced

    # ── Domain template substitution ─────────────────────────────────────────

    def test_param_substitution_simple(self):
        domain = [("date", ">=", "%(start_date)s")]
        params = {"start_date": "2026-01-01"}
        result = _apply_param_substitution(domain, params)
        self.assertEqual(result, [("date", ">=", "2026-01-01")])

    def test_param_substitution_no_match(self):
        """Domain without tokens is returned unchanged."""
        domain = [("state", "=", "done")]
        result = _apply_param_substitution(domain, {"start_date": "2026-01-01"})
        self.assertEqual(result, [("state", "=", "done")])

    def test_param_substitution_nested(self):
        """Operator strings and nested lists are handled correctly."""
        domain = ["&", ("date", ">=", "%(start)s"), ("date", "<=", "%(end)s")]
        params = {"start": "2026-01-01", "end": "2026-12-31"}
        result = _apply_param_substitution(domain, params)
        self.assertEqual(
            result,
            ["&", ("date", ">=", "2026-01-01"), ("date", "<=", "2026-12-31")],
        )

    @mute_logger("odoo.addons.spreadsheet_oca.models.spreadsheet_refresh_schedule")
    def test_param_substitution_unknown_param_no_error(self):
        """Unknown param name logs a warning but does not raise."""
        domain = [("date", ">=", "%(missing)s")]
        # Should not raise — logs a warning and leaves token in place.
        result = _apply_param_substitution(domain, {})
        self.assertEqual(result, [("date", ">=", "%(missing)s")])

    # ── Smart button count ────────────────────────────────────────────────────

    def test_smart_button_count(self):
        other_ss = self.env["spreadsheet.spreadsheet"].create({"name": "Other SS"})
        self._make_param(name="cnt_a")
        p2 = self._make_param(name="cnt_b")
        self.spreadsheet.invalidate_recordset()
        self.assertEqual(self.spreadsheet.input_param_count, 2)
        # Archiving reduces count.
        p2.write({"active": False})
        self.spreadsheet.invalidate_recordset()
        self.assertEqual(self.spreadsheet.input_param_count, 1)
        # Other spreadsheet count unaffected.
        self.assertEqual(other_ss.input_param_count, 0)

    # ── Action open input params ──────────────────────────────────────────────

    def test_action_open_input_params(self):
        action = self.spreadsheet.action_open_input_params()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "spreadsheet.input_param")
        self.assertIn(("spreadsheet_id", "=", self.spreadsheet.id), action["domain"])

    # ── Full refresh-cycle integration ────────────────────────────────────────

    def test_refresh_uses_params(self):
        """Param is synced and substituted in the domain during a refresh cycle."""
        self.spreadsheet.write({"spreadsheet_raw": self.raw_with_b3})
        param = self._make_param(name="filter_name")
        # Pivot domain references the param.
        raw = {
            "version": 1,
            "sheets": [
                {
                    "id": "s1",
                    "name": "Sheet1",
                    "cells": {"B3": {"content": "Administrator"}},
                }
            ],
            "pivots": {
                "1": {
                    "type": "ODOO",
                    "model": "res.partner",
                    "name": "Partners",
                    "domain": [("name", "=", "%(filter_name)s")],
                    "rows": [],
                    "columns": [],
                    "measures": [{"fieldName": "id", "aggregator": "count"}],
                }
            },
        }
        self.spreadsheet.write({"spreadsheet_raw": raw})
        schedule = self.env["spreadsheet.refresh.schedule"].create(
            {
                "name": "Integration Test",
                "spreadsheet_id": self.spreadsheet.id,
            }
        )
        schedule._run_refresh()
        # Param should have been synced.
        param.invalidate_recordset()
        self.assertEqual(param.current_value, "Administrator")
        self.assertTrue(schedule.last_run)

    # ── Controller endpoint logic ─────────────────────────────────────────────

    def test_controller_returns_param_dict(self):
        """The endpoint returns {name: current_value} for active params."""
        other_ss = self.env["spreadsheet.spreadsheet"].create({"name": "Ctrl SS"})
        p = self.env["spreadsheet.input_param"].create(
            {
                "name": "ctrl_param",
                "spreadsheet_id": other_ss.id,
                "cell_ref": "A1",
            }
        )
        p.write({"current_value": "test_value"})
        # Simulate what the controller does (model-level, no HTTP layer).
        params = self.env["spreadsheet.input_param"].search(
            [
                ("spreadsheet_id", "=", other_ss.id),
                ("active", "=", True),
            ]
        )
        result = {q.name: q.current_value for q in params}
        self.assertEqual(result, {"ctrl_param": "test_value"})
