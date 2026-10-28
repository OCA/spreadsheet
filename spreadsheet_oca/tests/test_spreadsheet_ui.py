# Copyright 2026 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestSpreadsheetUi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spreadsheet = cls.env["spreadsheet.spreadsheet"].create(
            {"name": "Tour spreadsheet", "owner_id": cls.env.ref("base.user_admin").id}
        )
        cls.partner_action = cls.env["ir.actions.act_window"].create(
            {
                "name": "Tour partners",
                "res_model": "res.partner",
                "view_mode": "list,pivot,graph",
            }
        )

    def _revision_commands(self, spreadsheet):
        revisions = self.env["spreadsheet.oca.revision"].search(
            [("model", "=", spreadsheet._name), ("res_id", "=", spreadsheet.id)]
        )
        return [
            command
            for revision in revisions
            for command in json.loads(revision.commands).get("commands", [])
        ]

    def test_edit_spreadsheet(self):
        self.start_tour(
            "/odoo/action-spreadsheet_oca.spreadsheet_spreadsheet_act_window",
            "spreadsheet_oca_edit",
            login="admin",
        )
        # "Save" writes the spreadsheet data (and drops the revisions)
        self.assertIn("=1+41", json.dumps(self.spreadsheet.spreadsheet_raw))

    def _test_insert(self, tour, command_type):
        spreadsheets = self.env["spreadsheet.spreadsheet"].search([])
        self.start_tour(f"/odoo/action-{self.partner_action.id}", tour, login="admin")
        new_spreadsheet = self.env["spreadsheet.spreadsheet"].search(
            [("id", "not in", spreadsheets.ids)]
        )
        self.assertEqual(len(new_spreadsheet), 1)
        self.assertIn(
            command_type,
            [cmd["type"] for cmd in self._revision_commands(new_spreadsheet)],
        )
        return new_spreadsheet

    def test_insert_pivot(self):
        spreadsheet = self._test_insert("spreadsheet_oca_insert_pivot", "ADD_PIVOT")
        self.assertIn(
            "ADD_GLOBAL_FILTER",
            [cmd["type"] for cmd in self._revision_commands(spreadsheet)],
        )
        # The revisions are replayed when the spreadsheet is opened again
        self.start_tour(
            f"/odoo/action-spreadsheet_oca.spreadsheet_spreadsheet_act_window"
            f"/{spreadsheet.id}",
            "spreadsheet_oca_reopen",
            login="admin",
        )

    def test_insert_list(self):
        self._test_insert("spreadsheet_oca_insert_list", "INSERT_ODOO_LIST")

    def test_insert_graph(self):
        self._test_insert("spreadsheet_oca_insert_graph", "CREATE_CHART")
