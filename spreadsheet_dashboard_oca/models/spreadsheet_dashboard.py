# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SpreadsheetDashboard(models.Model):
    _name = "spreadsheet.dashboard"
    _inherit = ["spreadsheet.dashboard", "spreadsheet.abstract"]

    active = fields.Boolean(default=True)
    spreadsheet_raw = fields.Serialized(
        inverse="_inverse_spreadsheet_raw", compute="_compute_spreadsheet_raw"
    )
    can_edit = fields.Boolean(compute="_compute_can_edit", search="_search_can_edit")

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

    def _compute_can_edit(self):
        """We can edit if the record doesn't have XML-ID, or the XML-ID is noupdate=1"""
        self.can_edit = True
        for record in self.filtered("id"):
            imd = self.env["ir.model.data"].search(
                [("model", "=", record._name), ("res_id", "=", record.id)]
            )
            if imd and imd.module != "__export__":
                record.can_edit = imd.noupdate

    @api.model
    def _search_can_edit(self, operator, value):
        if operator != "=":
            raise NotImplementedError(_("Search operation not supported"))
        if not isinstance(value, bool):
            raise ValidationError(_("The value has to be a boolean"))
        no_edit_ids = (
            self.env["ir.model.data"]
            .search(
                [
                    ("model", "=", self._name),
                    ("module", "!=", "__export__"),
                    ("noupdate", "=", 0),
                ]
            )
            .mapped("res_id")
        )
        if value:
            return [("id", "not in", no_edit_ids)]
        return [("id", "in", no_edit_ids)]
