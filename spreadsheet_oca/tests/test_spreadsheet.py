# Copyright 2026 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from io import BytesIO

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSpreadsheet(TransactionCase):
    def test_empty_spreadsheet_data(self):
        spreadsheet = self.env["spreadsheet.spreadsheet"].create({"name": "Empty"})
        data = spreadsheet.get_spreadsheet_data()
        self.assertEqual(data["name"], "Empty")
        self.assertEqual(data["mode"], "normal")
        self.assertEqual(data["spreadsheet_raw"]["sheets"][0]["id"], "sheet1")
        self.assertEqual(data["revisions"], [])

    def test_revisions(self):
        spreadsheet = self.env["spreadsheet.spreadsheet"].create({"name": "Rev"})
        message = {
            "type": "REMOTE_REVISION",
            "clientId": "client",
            "nextRevisionId": "rev-2",
            "serverRevisionId": "START_REVISION",
            "commands": [
                {
                    "type": "UPDATE_CELL",
                    "sheetId": "sheet1",
                    "col": 0,
                    "row": 0,
                    "content": "42",
                }
            ],
        }
        self.assertTrue(spreadsheet.send_spreadsheet_message(message))
        self.env.invalidate_all()
        revisions = spreadsheet.get_spreadsheet_data()["revisions"]
        self.assertEqual(len(revisions), 1)
        self.assertEqual(revisions[0]["nextRevisionId"], "rev-2")
        self.assertEqual(revisions[0]["commands"][0]["content"], "42")
        # Saving the data drops the revisions
        spreadsheet.spreadsheet_raw = {"sheets": [{"id": "sheet1", "name": "S"}]}
        self.assertFalse(spreadsheet.spreadsheet_revision_ids)
        self.assertEqual(spreadsheet.spreadsheet_raw["sheets"][0]["name"], "S")

    def test_import_xlsx(self):
        from openpyxl import Workbook

        workbook = Workbook()
        workbook.active["A1"] = "Hello"
        buffer = BytesIO()
        workbook.save(buffer)
        attachment = self.env["ir.attachment"].create(
            {"name": "test.xlsx", "raw": buffer.getvalue()}
        )
        action = self.env["spreadsheet.spreadsheet"].create_document_from_attachment(
            attachment.ids
        )
        spreadsheet = self.env["spreadsheet.spreadsheet"].browse(action["res_id"])
        self.assertEqual(spreadsheet.name, "test.xlsx")
        self.assertIn("xl/workbook.xml", spreadsheet.spreadsheet_raw)
        self.assertFalse(attachment.exists())
