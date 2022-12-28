# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json

from odoo import api, fields, models


class SpreadsheetSpreadsheet(models.Model):
    _name = "spreadsheet.spreadsheet"
    _description = "Spreadsheet"

    name = fields.Char()
    data = fields.Binary()
    raw = fields.Serialized(compute="_compute_raw", inverse="_inverse_raw")

    @api.depends("data")
    def _compute_raw(self):
        for dashboard in self:
            if dashboard.data:
                dashboard.raw = json.loads(
                    base64.decodebytes(dashboard.data).decode("UTF-8")
                )
            else:
                dashboard.raw = {}

    def _inverse_raw(self):
        for record in self:
            record.data = base64.encodebytes(json.dumps(record.raw).encode("UTF-8"))


class IrActionsActWindowView(models.Model):
    _inherit = "ir.actions.act_window.view"
    view_mode = fields.Selection(
        selection_add=[("spreadsheet", "Spreadsheet")],
        ondelete={"spreadsheet": "cascade"},
    )


class View(models.Model):
    _inherit = "ir.ui.view"
    type = fields.Selection(
        selection_add=[("spreadsheet", "Spreadsheet")],
        ondelete={"spreadsheet": "cascade"},
    )
