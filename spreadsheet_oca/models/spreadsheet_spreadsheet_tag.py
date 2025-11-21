# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from random import randint

from odoo import fields, models


class SpreadsheetSpreadsheetTags(models.Model):
    _name = "spreadsheet.spreadsheet.tag"
    _description = "Spreadsheet Tag"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(
        default=_get_default_color,
        help="Transparent tags are not visible in the kanban view",
    )

    _sql_constraints = [
        ("name_uniq", "unique (name)", "A tag with the same name already exists."),
    ]
