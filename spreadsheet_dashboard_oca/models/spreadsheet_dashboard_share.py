# Copyright 2026 Volkan Tasci
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class SpreadsheetDashboardShare(models.Model):
    _inherit = "spreadsheet.dashboard.share"

    @api.model
    def action_get_dashboard_shares(self, dashboard_id):
        """Return the shares of a dashboard the current user can see."""
        shares = self.search([("dashboard_id", "=", dashboard_id)])
        return [
            {
                "id": share.id,
                "full_url": share.full_url,
                "create_date": (
                    share.create_date.isoformat() if share.create_date else False
                ),
                "create_uid": (
                    share.create_uid.display_name if share.create_uid else False
                ),
                "name": share.name,
            }
            for share in shares
        ]

    @api.model
    def action_unshare(self, share_ids):
        """Revoke shares. ir.rule limits the user to the shares they may access."""
        self.browse(share_ids).unlink()
        return True

    @api.model
    def action_get_share_counts(self):
        """Return {dashboard_id: share_count} for shares visible to the user."""
        counts = self._read_group([], ["dashboard_id"], ["__count"])
        return {count[0].id: count[1] for count in counts if count[0]}
