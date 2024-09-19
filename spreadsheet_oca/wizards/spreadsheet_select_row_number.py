# Copyright 2024 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SpreadsheetSelectRowNumber(models.TransientModel):
    _name = "spreadsheet.select.row.number"
    _description = "Select number of rows to duplicate row"

    dynamic_rows = fields.Boolean()
    number_of_rows = fields.Integer()
    can_have_dynamic_cols = fields.Boolean()
    dynamic_cols = fields.Boolean()
    number_of_cols = fields.Integer()
