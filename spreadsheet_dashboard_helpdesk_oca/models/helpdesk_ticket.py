# Copyright 2026 Domatix
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    hours_to_assign = fields.Float(
        compute="_compute_hours_metrics",
        store=True,
        aggregator="avg",
    )
    hours_to_close = fields.Float(
        compute="_compute_hours_metrics",
        store=True,
        aggregator="avg",
    )

    @api.depends("create_date", "assigned_date", "closed_date")
    def _compute_hours_metrics(self):
        for ticket in self:
            hours_to_assign = 0.0
            hours_to_close = 0.0
            if ticket.create_date and ticket.assigned_date:
                delta = ticket.assigned_date - ticket.create_date
                hours_to_assign = delta.total_seconds() / 3600
            if ticket.create_date and ticket.closed_date:
                delta = ticket.closed_date - ticket.create_date
                hours_to_close = delta.total_seconds() / 3600
            ticket.hours_to_assign = hours_to_assign
            ticket.hours_to_close = hours_to_close
