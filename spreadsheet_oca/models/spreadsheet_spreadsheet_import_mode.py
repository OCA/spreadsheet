# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SpreadsheetSpreadsheetImportMode(models.Model):
    _name = "spreadsheet.spreadsheet.import.mode"
    _description = "Import Mode"
    _order = "sequence asc"
    _rec_name = "name"

    sequence = fields.Integer(default=20)
    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    group_ids = fields.Many2many("res.groups")
