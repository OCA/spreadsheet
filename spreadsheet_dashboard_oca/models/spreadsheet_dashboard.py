# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo import fields, models


class SpreadsheetDashboard(models.Model):
    _inherit = "spreadsheet.dashboard"

    raw = fields.Binary(inverse="_inverse_raw")

    def _inverse_raw(self):
        for record in self:
            record.data = base64.encodebytes(record.raw)

    def open_spreadsheet(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "action_spreadsheet_oca",
            "params": {"spreadsheet_id": self.id, "model": self._name},
        }
