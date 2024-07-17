# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SpreadsheetSpreadsheetImport(models.TransientModel):

    _inherit = "spreadsheet.spreadsheet.import"

    dashboard_id = fields.Many2one("spreadsheet.dashboard")
    dashboard_group_id = fields.Many2one("spreadsheet.dashboard.group")

    def _create_spreadsheet_dashboard_vals(self):
        return {
            "name": self.name,
            "dashboard_group_id": self.dashboard_group_id.id,
        }

    def _insert_pivot_dashboard_spreadsheet(self):
        dashboard = self.env["spreadsheet.dashboard"].create(
            self._create_spreadsheet_dashboard_vals()
        )
        import_data = self.import_data
        import_data["name"] = self.datasource_name
        import_data["new"] = 1
        if self.dynamic:
            import_data["dyn_number_of_rows"] = self.number_of_rows
        return {
            "type": "ir.actions.client",
            "tag": "action_spreadsheet_oca",
            "params": {
                "model": dashboard._name,
                "spreadsheet_id": dashboard.id,
                "import_data": import_data,
            },
        }

    def _insert_pivot_dashboard(self, new_sheet=False):
        import_data = self.import_data
        import_data["name"] = self.datasource_name
        import_data["new_sheet"] = new_sheet
        if self.dynamic:
            import_data["dyn_number_of_rows"] = self.number_of_rows
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
