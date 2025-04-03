# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SpreadsheetDashboard(models.Model):
    _name = "spreadsheet.dashboard"
    _inherit = ["spreadsheet.dashboard", "spreadsheet.abstract"]

    active = fields.Boolean(default=True)
    can_edit = fields.Boolean(compute="_compute_can_edit", search="_search_can_edit")

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
