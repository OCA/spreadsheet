# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SpreadsheetSpreadsheetImport(models.TransientModel):

    _inherit = "spreadsheet.spreadsheet.import"

    dashboard_id = fields.Many2one("spreadsheet.dashboard")

    def _insert_pivot_dashboard(self, new_sheet=False):
        import_data = self.import_data
        import_data["name"] = self.name
        import_data["new_sheet"] = new_sheet
        return {
            "type": "ir.actions.client",
            "tag": "action_spreadsheet_oca",
            "params": {
                "model": "spreadsheet.dashboard",
                "spreadsheet_id": self.dashboard_id.id,
                "import_data": import_data,
            },
        }

    def _insert_pivot_dashboard_sheet(self):
        return self._insert_pivot_dashboard(True)
