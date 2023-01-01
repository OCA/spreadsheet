# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo import fields, models


class SpreadsheetDashboard(models.Model):
    _name = "spreadsheet.dashboard"
    _inherit = ["spreadsheet.dashboard", "spreadsheet.abstract"]

    raw = fields.Binary(inverse="_inverse_raw")

    def _inverse_raw(self):
        for record in self:
            record.data = base64.encodebytes(record.raw)
