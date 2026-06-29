# Copyright 2026 Domatix
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.helpdesk_mgmt.tests.common import TestHelpdeskTicketBase


@tagged("post_install", "-at_install")
class TestHelpdeskTicketMetrics(TestHelpdeskTicketBase):
    def test_hours_metrics(self):
        now = fields.Datetime.now()
        ticket = self.env["helpdesk.ticket"].create(
            {
                "name": "Broken printer",
                "description": "<p>Test</p>",
                "team_id": self.team_a.id,
            }
        )
        ticket.write(
            {
                "assigned_date": now + timedelta(hours=2),
                "closed_date": now + timedelta(hours=5),
            }
        )
        self.assertAlmostEqual(ticket.hours_to_assign, 2.0, places=2)
        self.assertAlmostEqual(ticket.hours_to_close, 5.0, places=2)
