# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Tests for spreadsheet.alert (threshold alerts / KPI watches).
"""

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from ..models.cell_ref import parse_cell_ref as _parse_cell_ref


class TestParseCellRef(TransactionCase):
    """Unit tests for the _parse_cell_ref helper (pure logic, no DB)."""

    def test_simple(self):
        self.assertEqual(_parse_cell_ref("A1"), (0, 0))
        self.assertEqual(_parse_cell_ref("B3"), (1, 2))
        self.assertEqual(_parse_cell_ref("Z1"), (25, 0))

    def test_multi_letter(self):
        col, row = _parse_cell_ref("AA1")
        self.assertEqual(col, 26)
        self.assertEqual(row, 0)

    def test_case_insensitive(self):
        self.assertEqual(_parse_cell_ref("b3"), _parse_cell_ref("B3"))

    def test_invalid(self):
        self.assertEqual(_parse_cell_ref(""), (None, None))
        self.assertEqual(_parse_cell_ref("A0"), (None, None))  # row must be ≥ 1
        self.assertEqual(_parse_cell_ref("12"), (None, None))


class TestSpreadsheetAlert(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spreadsheet = cls.env["spreadsheet.spreadsheet"].create(
            {"name": "Alert Test Spreadsheet"}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Alert Subscriber"})

    def _make_alert(self, **kwargs):
        defaults = {
            "name": "Revenue Alert",
            "spreadsheet_id": self.spreadsheet.id,
            "cell_ref": "B3",
            "operator": ">",
            "threshold": 1000.0,
            "trigger_mode": "edge",
        }
        defaults.update(kwargs)
        return self.env["spreadsheet.alert"].create(defaults)

    def _set_cell_value(self, value, col="B", row=3):
        """Write a cell value into spreadsheet_raw for testing."""
        cell_addr = f"{col.upper()}{row}"
        raw = {
            "version": 1,
            "sheets": [
                {
                    "id": "sheet1",
                    "name": "Sheet1",
                    "cells": {
                        cell_addr: {"content": str(value)},
                    },
                }
            ],
        }
        self.spreadsheet.write({"spreadsheet_raw": raw})

    # ── Validation ────────────────────────────────────────────────────────────

    def test_invalid_cell_ref_raises(self):
        with self.assertRaises(ValidationError):
            self._make_alert(cell_ref="A0")

    def test_valid_cell_ref_accepted(self):
        alert = self._make_alert(cell_ref="C12")
        self.assertEqual(alert.cell_ref, "C12")

    # ── _check_condition ──────────────────────────────────────────────────────

    def test_operators(self):
        alert = self._make_alert(operator=">", threshold=100.0)
        self.assertTrue(alert._check_condition(101.0))
        self.assertFalse(alert._check_condition(100.0))

        alert.operator = ">="
        self.assertTrue(alert._check_condition(100.0))

        alert.operator = "<"
        self.assertTrue(alert._check_condition(99.0))
        self.assertFalse(alert._check_condition(100.0))

        alert.operator = "=="
        self.assertTrue(alert._check_condition(100.0))
        self.assertFalse(alert._check_condition(99.9))

        alert.operator = "!="
        self.assertTrue(alert._check_condition(99.0))
        self.assertFalse(alert._check_condition(100.0))

    # ── _read_cell_value ──────────────────────────────────────────────────────

    def test_read_cell_value_numeric(self):
        self._set_cell_value(42.5)
        alert = self._make_alert(cell_ref="B3")
        self.assertAlmostEqual(alert._read_cell_value(), 42.5)

    def test_read_cell_value_empty_sheet(self):
        self.spreadsheet.write({"spreadsheet_raw": {}})
        alert = self._make_alert(cell_ref="B3")
        self.assertIsNone(alert._read_cell_value())

    def test_read_cell_value_missing_cell(self):
        self._set_cell_value(10, col="A", row=1)
        alert = self._make_alert(cell_ref="Z99")
        self.assertIsNone(alert._read_cell_value())

    def test_read_cell_value_by_sheet_name(self):
        raw = {
            "version": 1,
            "sheets": [
                {
                    "id": "s1",
                    "name": "Summary",
                    "cells": {"B3": {"content": "77"}},
                },
                {"id": "s2", "name": "Data", "cells": {"B3": {"content": "99"}}},
            ],
        }
        self.spreadsheet.write({"spreadsheet_raw": raw})
        alert = self._make_alert(cell_ref="B3", sheet_name="Data")
        self.assertAlmostEqual(alert._read_cell_value(), 99.0)

    # ── Edge mode ─────────────────────────────────────────────────────────────

    def test_edge_mode_fires_once_on_crossing(self):
        self._set_cell_value(1500)
        alert = self._make_alert(operator=">", threshold=1000.0, trigger_mode="edge")
        self.assertFalse(alert.last_state)

        msg_count_before = self.env["mail.message"].search_count(
            [
                ("res_id", "=", self.spreadsheet.id),
                ("model", "=", "spreadsheet.spreadsheet"),
            ]
        )
        alert._evaluate()
        msg_count_after = self.env["mail.message"].search_count(
            [
                ("res_id", "=", self.spreadsheet.id),
                ("model", "=", "spreadsheet.spreadsheet"),
            ]
        )
        self.assertGreater(msg_count_after, msg_count_before)
        self.assertTrue(alert.last_state)

        # Second evaluation: already in alert state → no new notification
        msg_count_before2 = msg_count_after
        alert._evaluate()
        msg_count_after2 = self.env["mail.message"].search_count(
            [
                ("res_id", "=", self.spreadsheet.id),
                ("model", "=", "spreadsheet.spreadsheet"),
            ]
        )
        self.assertEqual(msg_count_before2, msg_count_after2)

    def test_edge_mode_no_fire_below_threshold(self):
        self._set_cell_value(500)
        alert = self._make_alert(operator=">", threshold=1000.0, trigger_mode="edge")
        msg_count_before = self.env["mail.message"].search_count(
            [
                ("res_id", "=", self.spreadsheet.id),
                ("model", "=", "spreadsheet.spreadsheet"),
            ]
        )
        alert._evaluate()
        msg_count_after = self.env["mail.message"].search_count(
            [
                ("res_id", "=", self.spreadsheet.id),
                ("model", "=", "spreadsheet.spreadsheet"),
            ]
        )
        self.assertEqual(msg_count_before, msg_count_after)
        self.assertFalse(alert.last_state)

    def test_edge_reset_allows_re_trigger(self):
        self._set_cell_value(1500)
        alert = self._make_alert(operator=">", threshold=1000.0, trigger_mode="edge")
        alert._evaluate()  # fires
        self.assertTrue(alert.last_state)
        alert.action_reset_state()
        self.assertFalse(alert.last_state)

        msg_before = self.env["mail.message"].search_count(
            [
                ("res_id", "=", self.spreadsheet.id),
                ("model", "=", "spreadsheet.spreadsheet"),
            ]
        )
        alert._evaluate()  # fires again after reset
        msg_after = self.env["mail.message"].search_count(
            [
                ("res_id", "=", self.spreadsheet.id),
                ("model", "=", "spreadsheet.spreadsheet"),
            ]
        )
        self.assertGreater(msg_after, msg_before)

    # ── Level mode ────────────────────────────────────────────────────────────

    def test_level_mode_fires_every_cycle(self):
        self._set_cell_value(1500)
        alert = self._make_alert(operator=">", threshold=1000.0, trigger_mode="level")

        for i in range(3):
            msg_before = self.env["mail.message"].search_count(
                [
                    ("res_id", "=", self.spreadsheet.id),
                    ("model", "=", "spreadsheet.spreadsheet"),
                ]
            )
            alert._evaluate()
            msg_after = self.env["mail.message"].search_count(
                [
                    ("res_id", "=", self.spreadsheet.id),
                    ("model", "=", "spreadsheet.spreadsheet"),
                ]
            )
            self.assertGreater(
                msg_after, msg_before, f"Expected notification on cycle {i + 1}"
            )

    # ── Cron dispatcher ───────────────────────────────────────────────────────

    def test_cron_evaluates_all_active(self):
        self._set_cell_value(2000)
        alert1 = self._make_alert(operator=">", threshold=1000.0)
        alert2 = self._make_alert(
            name="Low Stock", operator="<", threshold=5.0, cell_ref="B3"
        )

        # Both should update last_checked after cron run
        self.env["spreadsheet.alert"]._cron_evaluate_all()
        self.assertTrue(alert1.last_checked)
        self.assertTrue(alert2.last_checked)

    def test_cron_skips_inactive(self):
        alert = self._make_alert(active=False, operator=">", threshold=1000.0)
        self.env["spreadsheet.alert"]._cron_evaluate_all()
        self.assertFalse(alert.last_checked)

    # ── Smart button ──────────────────────────────────────────────────────────

    def test_smart_button_count(self):
        self.assertEqual(self.spreadsheet.alert_count, 0)
        self._make_alert()
        self._make_alert(name="Alert 2", cell_ref="C5")
        self.spreadsheet.invalidate_recordset()
        self.assertEqual(self.spreadsheet.alert_count, 2)
