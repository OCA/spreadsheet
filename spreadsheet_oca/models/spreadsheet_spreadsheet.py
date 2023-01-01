# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo import api, fields, models


class SpreadsheetSpreadsheet(models.Model):
    _name = "spreadsheet.spreadsheet"
    _inherit = "spreadsheet.abstract"
    _description = "Spreadsheet"

    data = fields.Binary()
    raw = fields.Binary(compute="_compute_raw", inverse="_inverse_raw")

    @api.depends("data")
    def _compute_raw(self):
        for dashboard in self:
            if dashboard.data:
                dashboard.raw = base64.decodebytes(dashboard.data).decode("UTF-8")
            else:
                dashboard.raw = "{}"

    def _inverse_raw(self):
        for record in self:
            record.data = base64.encodebytes(record.raw)
