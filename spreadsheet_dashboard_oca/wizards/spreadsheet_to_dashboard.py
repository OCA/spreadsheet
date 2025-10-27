# Copyright 2025 Open User Systems
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo import api, fields, models


class SpreadsheetToDashboard(models.TransientModel):
    _name = "spreadsheet.to.dashboard"
    _description = "Create dashboard from spreadsheet"

    name = fields.Char(
        "Dashboard Name",
        required=True,
        compute="_compute_name",
        store=True,
        readonly=False,
        precompute=True,
    )
    spreadsheet_id = fields.Many2one(
        "spreadsheet.spreadsheet",
        readonly=True,
        required=True,
    )
    dashboard_group_id = fields.Many2one(
        "spreadsheet.dashboard.group", string="Dashboard Section", required=True
    )
    group_ids = fields.Many2many(
        "res.groups",
        default=lambda self: self._default_group_ids(),
        string="User Groups",
    )

    def _default_group_ids(self):
        return self.env["spreadsheet.dashboard"].default_get(["group_ids"])["group_ids"]

    @api.depends("spreadsheet_id.name")
    def _compute_name(self):
        for rec in self:
            rec.name = rec.spreadsheet_id.name

    def create_dashboard(self):
        self.ensure_one()
        spreadsheet_data = self.spreadsheet_id.get_spreadsheet_data()
        spreadsheet_raw = spreadsheet_data["spreadsheet_raw"]
        dashboard = self.env["spreadsheet.dashboard"].create(
            {
                "name": self.name,
                "dashboard_group_id": self.dashboard_group_id.id,
                "group_ids": self.group_ids.ids,
                "spreadsheet_data": json.dumps(spreadsheet_raw),
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "action_spreadsheet_dashboard",
            "name": self.name,
            "params": {
                "dashboard_id": dashboard.id,
            },
        }
