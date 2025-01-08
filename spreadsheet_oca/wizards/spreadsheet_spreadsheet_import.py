# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SpreadsheetSpreadsheetImport(models.TransientModel):
    _name = "spreadsheet.spreadsheet.import"
    _description = "Import data to spreadsheet"

    @api.model
    def _default_mode_id(self):
        return self.env["spreadsheet.spreadsheet.import.mode"].search([], limit=1).id

    name = fields.Char()
    datasource_name = fields.Char()
    mode_id = fields.Many2one(
        "spreadsheet.spreadsheet.import.mode",
        required=True,
        default=lambda r: r._default_mode_id(),
    )
    mode = fields.Char(related="mode_id.code")
    import_data = fields.Serialized()
    spreadsheet_id = fields.Many2one("spreadsheet.spreadsheet")
    can_be_dynamic = fields.Boolean()
    can_have_dynamic_cols = fields.Boolean()
    is_tree = fields.Boolean()
    dynamic = fields.Boolean(
        "Dynamic Rows",
        help="This field allows you to generate tables that its rows are updated with"
        " the filters set in the spreadsheets.",
    )
    dynamic_cols = fields.Boolean(
        "Dynamic Columns",
        help="This field allows you to generate tables that its cols are updated with"
        " the filters set in the spreadsheets.",
    )
    number_of_rows = fields.Integer()
    number_of_cols = fields.Integer("Number of Columns")

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
        import_data["name"] = self.datasource_name
        import_data["new"] = 1
        if self.dynamic:
            import_data["dyn_number_of_rows"] = self.number_of_rows
        if self.dynamic_cols:
            import_data["dyn_number_of_cols"] = self.number_of_cols
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
        import_data["name"] = self.datasource_name
        import_data["new_sheet"] = new_sheet
        if self.dynamic:
            import_data["dyn_number_of_rows"] = self.number_of_rows
        if self.dynamic_cols:
            import_data["dyn_number_of_cols"] = self.number_of_cols
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
