# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SpreadsheetSpreadsheetImport(models.TransientModel):

    _name = "spreadsheet.spreadsheet.import"
    _description = "Import data to spreadsheet"

    @api.model
    def _default_mode_id(self):
        return self.env["spreadsheet.spreadsheet.import.mode"].search([], limit=1).id

    name = fields.Char(required=True)
    mode_id = fields.Many2one(
        "spreadsheet.spreadsheet.import.mode",
        required=True,
        default=lambda r: r._default_mode_id(),
    )
    mode = fields.Char(related="mode_id.code")
    import_data = fields.Serialized()
    spreadsheet_id = fields.Many2one("spreadsheet.spreadsheet")

    def insert_pivot(self):
        self.ensure_one()
        return getattr(self, "_insert_pivot_%s" % self.mode_id.code)()

    def _create_spreadsheet_vals(self):
        return {"name": self.name}

    def _insert_pivot_new(self):
        spreadsheet = self.env["spreadsheet.spreadsheet"].create(
            self._create_spreadsheet_vals()
        )
        import_data = self.import_data
        import_data["new"] = 1
        return {
            "type": "ir.actions.client",
            "tag": "action_spreadsheet_oca",
            "params": {
                "model": spreadsheet._name,
                "spreadsheet_id": spreadsheet.id,
                "import_data": import_data,
            },
        }

    def _insert_pivot_add(self, new_sheet=False):
        import_data = self.import_data
        import_data["name"] = self.name
        import_data["new_sheet"] = new_sheet
        return {
            "type": "ir.actions.client",
            "tag": "action_spreadsheet_oca",
            "params": {
                "model": "spreadsheet.spreadsheet",
                "spreadsheet_id": self.spreadsheet_id.id,
                "import_data": import_data,
            },
        }

    def _insert_pivot_add_sheet(self):
        return self._insert_pivot_add(True)
