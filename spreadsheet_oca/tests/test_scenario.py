# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Tests for spreadsheet.scenario (named scenarios / what-if manager).
"""

import json

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestSpreadsheetScenario(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spreadsheet = cls.env["spreadsheet.spreadsheet"].create(
            {"name": "Scenario Test Spreadsheet"}
        )
        # Minimal valid o-spreadsheet raw JSON with two sheets.
        cls.raw_with_sheets = {
            "version": 1,
            "sheets": [
                {
                    "id": "sheet1",
                    "name": "Sheet1",
                    "cells": {
                        "B3": {"content": "50000"},
                    },
                },
                {
                    "id": "sheet2",
                    "name": "Assumptions",
                    "cells": {
                        "C5": {"content": "0.08"},
                    },
                },
            ],
        }

    def _make_scenario(self, **kwargs):
        defaults = {
            "name": "Base Case",
            "spreadsheet_id": self.spreadsheet.id,
        }
        defaults.update(kwargs)
        return self.env["spreadsheet.scenario"].create(defaults)

    # ── Basic create ──────────────────────────────────────────────────────────

    def test_create_scenario(self):
        scenario = self._make_scenario(name="Optimistic")
        self.assertEqual(scenario.name, "Optimistic")
        self.assertEqual(scenario.spreadsheet_id, self.spreadsheet)
        self.assertFalse(scenario.is_base)
        self.assertTrue(scenario.active)
        self.assertFalse(scenario.cell_overrides)

    # ── override_count ────────────────────────────────────────────────────────

    def test_override_count(self):
        overrides = json.dumps({"B3": 125000, "C5": 0.15, "D7": "hello"})
        scenario = self._make_scenario(cell_overrides=overrides)
        self.assertEqual(scenario.override_count, 3)

    def test_override_count_empty(self):
        scenario = self._make_scenario()
        self.assertEqual(scenario.override_count, 0)

    def test_override_count_blank_string(self):
        scenario = self._make_scenario(cell_overrides="   ")
        self.assertEqual(scenario.override_count, 0)

    # ── Validation: JSON format ───────────────────────────────────────────────

    def test_invalid_json_raises(self):
        with self.assertRaises(ValidationError):
            self._make_scenario(cell_overrides="this is not json!@#")

    def test_valid_json_non_dict_raises(self):
        """Top-level JSON array should be rejected."""
        with self.assertRaises(ValidationError):
            self._make_scenario(cell_overrides='["B3", "C5"]')

    def test_valid_json_accepted(self):
        overrides = json.dumps({"B3": 100, "C5": 0.2, "D7": None, "E9": True})
        scenario = self._make_scenario(cell_overrides=overrides)
        self.assertEqual(scenario.override_count, 4)

    # ── Validation: cell ref format ───────────────────────────────────────────

    def test_invalid_cell_ref_raises(self):
        """Keys that don't match the cell reference pattern must be rejected."""
        with self.assertRaises(ValidationError):
            self._make_scenario(cell_overrides=json.dumps({"NOTACELL": 1}))

    def test_invalid_cell_ref_row_zero_raises(self):
        """Row numbers must be >= 1."""
        with self.assertRaises(ValidationError):
            self._make_scenario(cell_overrides=json.dumps({"B0": 1}))

    def test_invalid_cell_ref_no_letters_raises(self):
        """Pure digit keys like '123' must be rejected."""
        with self.assertRaises(ValidationError):
            self._make_scenario(cell_overrides=json.dumps({"123": 1}))

    def test_bare_cell_ref_accepted(self):
        """'B3' without sheet prefix is valid."""
        scenario = self._make_scenario(cell_overrides=json.dumps({"B3": 99}))
        self.assertEqual(scenario.override_count, 1)

    def test_sheet_prefixed_cell_ref_accepted(self):
        """'Sheet1!B3' format is valid."""
        scenario = self._make_scenario(
            cell_overrides=json.dumps({"Sheet1!B3": 125000, "Assumptions!C5": 0.12})
        )
        self.assertEqual(scenario.override_count, 2)

    def test_invalid_value_type_raises(self):
        """Dict values must be int/float/str/bool/None. A list is not allowed."""
        with self.assertRaises(ValidationError):
            self._make_scenario(cell_overrides=json.dumps({"B3": [1, 2, 3]}))

    # ── Constraint: single base per spreadsheet ───────────────────────────────

    def test_duplicate_base_raises(self):
        """Two is_base=True scenarios on the same spreadsheet must raise."""
        self._make_scenario(name="Base v1", is_base=True)
        with self.assertRaises(ValidationError):
            self._make_scenario(name="Base v2", is_base=True)

    def test_two_non_base_scenarios_allowed(self):
        """Multiple non-base scenarios on the same spreadsheet are fine."""
        s1 = self._make_scenario(name="Optimistic")
        s2 = self._make_scenario(name="Pessimistic")
        self.assertTrue(s1.id)
        self.assertTrue(s2.id)

    def test_base_on_different_spreadsheets_allowed(self):
        """Each spreadsheet can have its own base scenario."""
        other = self.env["spreadsheet.spreadsheet"].create({"name": "Other Sheet"})
        s1 = self._make_scenario(name="Base for main", is_base=True)
        s2 = self.env["spreadsheet.scenario"].create(
            {
                "name": "Base for other",
                "spreadsheet_id": other.id,
                "is_base": True,
            }
        )
        self.assertTrue(s1.is_base)
        self.assertTrue(s2.is_base)

    # ── action_apply_to_copy ──────────────────────────────────────────────────

    def test_apply_to_copy_creates_new_spreadsheet(self):
        """action_apply_to_copy returns an act_window and creates a new record."""
        self.spreadsheet.write({"spreadsheet_raw": self.raw_with_sheets})
        scenario = self._make_scenario(
            name="High Revenue",
            cell_overrides=json.dumps({"B3": 200000}),
        )
        count_before = self.env["spreadsheet.spreadsheet"].search_count([])
        action = scenario.action_apply_to_copy()
        count_after = self.env["spreadsheet.spreadsheet"].search_count([])

        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(count_after, count_before + 1)

    def test_apply_to_copy_correct_name(self):
        """The new spreadsheet should include both parent and scenario names."""
        self.spreadsheet.write({"spreadsheet_raw": self.raw_with_sheets})
        scenario = self._make_scenario(name="Pessimistic")
        action = scenario.action_apply_to_copy()
        new_id = action["res_id"]
        new_sheet = self.env["spreadsheet.spreadsheet"].browse(new_id)
        self.assertIn("Scenario Test Spreadsheet", new_sheet.name)
        self.assertIn("Pessimistic", new_sheet.name)

    def test_apply_to_copy_writes_cell(self):
        """The new spreadsheet raw has the correct cell value from the override."""
        self.spreadsheet.write({"spreadsheet_raw": self.raw_with_sheets})
        # B3 → col_idx=1, row_idx=2
        scenario = self._make_scenario(
            name="Override B3",
            cell_overrides=json.dumps({"B3": 999999}),
        )
        action = scenario.action_apply_to_copy()
        new_id = action["res_id"]
        new_sheet = self.env["spreadsheet.spreadsheet"].browse(new_id)
        new_raw = new_sheet.spreadsheet_raw
        cell_content = new_raw["sheets"][0]["cells"]["B3"]["content"]
        self.assertEqual(cell_content, "999999")

    def test_apply_to_copy_with_sheet_prefix(self):
        """'Sheet1!B3' prefix routes the override to the correct sheet."""
        self.spreadsheet.write({"spreadsheet_raw": self.raw_with_sheets})
        # Assumptions!C5 → sheet "Assumptions", col_idx=2, row_idx=4
        scenario = self._make_scenario(
            name="Rate Change",
            cell_overrides=json.dumps({"Assumptions!C5": 0.12}),
        )
        action = scenario.action_apply_to_copy()
        new_id = action["res_id"]
        new_sheet = self.env["spreadsheet.spreadsheet"].browse(new_id)
        new_raw = new_sheet.spreadsheet_raw
        # Assumptions is sheets[1]
        cell_content = new_raw["sheets"][1]["cells"]["C5"]["content"]
        self.assertEqual(cell_content, "0.12")

    def test_apply_does_not_modify_original(self):
        """action_apply_to_copy must leave the source spreadsheet_raw unchanged."""
        self.spreadsheet.write({"spreadsheet_raw": self.raw_with_sheets})
        original_raw = dict(self.spreadsheet.spreadsheet_raw)
        original_cell = self.spreadsheet.spreadsheet_raw["sheets"][0]["cells"]["B3"][
            "content"
        ]
        scenario = self._make_scenario(
            name="Change B3",
            cell_overrides=json.dumps({"B3": 777}),
        )
        scenario.action_apply_to_copy()
        self.spreadsheet.invalidate_recordset()
        after_cell = self.spreadsheet.spreadsheet_raw["sheets"][0]["cells"]["B3"][
            "content"
        ]
        self.assertEqual(original_cell, after_cell)
        # Sheet count must not have changed
        self.assertEqual(
            len(original_raw.get("sheets", [])),
            len(self.spreadsheet.spreadsheet_raw.get("sheets", [])),
        )

    def test_apply_to_copy_creates_cell_if_missing(self):
        """Override of a cell not in the raw JSON should create it."""
        self.spreadsheet.write({"spreadsheet_raw": self.raw_with_sheets})
        # Z99 does not exist in raw_with_sheets
        scenario = self._make_scenario(
            name="New Cell",
            cell_overrides=json.dumps({"Z99": 42}),
        )
        action = scenario.action_apply_to_copy()
        new_id = action["res_id"]
        new_sheet = self.env["spreadsheet.spreadsheet"].browse(new_id)
        new_raw = new_sheet.spreadsheet_raw
        cell_content = new_raw["sheets"][0]["cells"]["Z99"]["content"]
        self.assertEqual(cell_content, "42")

    def test_apply_to_copy_no_overrides(self):
        """A scenario with no overrides still creates a copy successfully."""
        self.spreadsheet.write({"spreadsheet_raw": self.raw_with_sheets})
        scenario = self._make_scenario(name="Empty Scenario")
        count_before = self.env["spreadsheet.spreadsheet"].search_count([])
        action = scenario.action_apply_to_copy()
        count_after = self.env["spreadsheet.spreadsheet"].search_count([])
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(count_after, count_before + 1)

    # ── action_export_comparison ──────────────────────────────────────────────

    def test_export_comparison_returns_notification(self):
        """action_export_comparison returns a display_notification action."""
        self.spreadsheet.write({"spreadsheet_raw": self.raw_with_sheets})
        scenario = self._make_scenario(
            name="Compare Me",
            cell_overrides=json.dumps({"B3": 150000}),
        )
        action = scenario.action_export_comparison()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "display_notification")
        self.assertIn("params", action)

    def test_export_comparison_no_overrides(self):
        """Comparison with no overrides returns an informational notification."""
        scenario = self._make_scenario(name="Empty")
        action = scenario.action_export_comparison()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(action["params"]["type"], "info")

    # ── Smart button / scenario_count ─────────────────────────────────────────

    def test_smart_button_count(self):
        """scenario_count on spreadsheet reflects active scenario count."""
        self.assertEqual(self.spreadsheet.scenario_count, 0)
        self._make_scenario(name="S1")
        self._make_scenario(name="S2")
        self._make_scenario(name="S3 Archived", active=False)
        self.spreadsheet.invalidate_recordset()
        self.assertEqual(self.spreadsheet.scenario_count, 2)

    # ── action_open_scenarios ─────────────────────────────────────────────────

    def test_action_open_scenarios(self):
        """action_open_scenarios returns an act_window with correct domain."""
        action = self.spreadsheet.action_open_scenarios()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "spreadsheet.scenario")
        self.assertIn(("spreadsheet_id", "=", self.spreadsheet.id), action["domain"])
        self.assertEqual(
            action["context"].get("default_spreadsheet_id"), self.spreadsheet.id
        )
