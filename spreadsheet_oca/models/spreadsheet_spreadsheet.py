# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json

from odoo import _, api, fields, models


class SpreadsheetSpreadsheet(models.Model):
    _name = "spreadsheet.spreadsheet"
    _inherit = "spreadsheet.abstract"
    _description = "Spreadsheet"

    data = fields.Binary()
    filename = fields.Char(compute="_compute_filename")
    spreadsheet_raw = fields.Serialized(
        compute="_compute_spreadsheet_raw", inverse="_inverse_spreadsheet_raw"
    )
    owner_id = fields.Many2one(
        "res.users", required=True, default=lambda r: r.env.user.id
    )
    contributor_ids = fields.Many2many(
        "res.users",
        relation="spreadsheet_contributor",
        column1="spreadsheet_id",
        column2="user_id",
        string="Contributors",
    )
    reader_ids = fields.Many2many(
        "res.users",
        relation="spreadsheet_reader",
        column1="spreadsheet_id",
        column2="user_id",
        string="Readers",
    )

    @api.depends("name")
    def _compute_filename(self):
        for record in self:
            record.filename = "%s.json" % (self.name or _("Unnamed"))

    @api.depends("data")
    def _compute_spreadsheet_raw(self):
        for dashboard in self:
            if dashboard.data:
                dashboard.spreadsheet_raw = json.loads(
                    base64.decodebytes(dashboard.data).decode("UTF-8")
                )
            else:
                dashboard.spreadsheet_raw = {}

    def _inverse_spreadsheet_raw(self):
        for record in self:
            record.data = base64.encodebytes(
                json.dumps(record.spreadsheet_raw).encode("UTF-8")
            )
