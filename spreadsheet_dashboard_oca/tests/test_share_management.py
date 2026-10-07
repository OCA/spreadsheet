# Copyright 2026 Volkan Tasci
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError
from odoo.tests import HttpCase, new_test_user

from odoo.addons.spreadsheet_dashboard.tests.common import DashboardTestCommon


class TestShareManagement(DashboardTestCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user2 = new_test_user(cls.env, login="Bob")
        cls.user2.group_ids |= cls.group
        cls.manager = new_test_user(
            cls.env,
            login="Manager",
            groups="spreadsheet_dashboard.group_dashboard_manager",
        )

    def _share_as(self, user, dashboard):
        return (
            self.env["spreadsheet.dashboard.share"]
            .with_user(user)
            .create(
                {
                    "dashboard_id": dashboard.id,
                    "spreadsheet_data": dashboard.spreadsheet_data,
                }
            )
        )

    def _get_shares(self, user, dashboard):
        return (
            self.env["spreadsheet.dashboard.share"]
            .with_user(user)
            .action_get_dashboard_shares(dashboard.id)
        )

    def _get_share_counts(self, user):
        return (
            self.env["spreadsheet.dashboard.share"]
            .with_user(user)
            .action_get_share_counts()
        )

    def _unshare_as(self, user, share):
        return (
            self.env["spreadsheet.dashboard.share"]
            .with_user(user)
            .action_unshare([share.id])
        )

    def test_share_flow_of_a_user(self):
        """A user manages their own shares, and only those."""
        dashboard = self.create_dashboard()
        self.assertNotIn(dashboard.id, self._get_share_counts(self.user))
        own_share = self._share_as(self.user, dashboard)
        other_share = self._share_as(self.user2, dashboard)

        shares = self._get_shares(self.user, dashboard)
        self.assertEqual(
            shares,
            [
                {
                    "id": own_share.id,
                    "full_url": own_share.full_url,
                    "create_date": own_share.create_date.isoformat(),
                    "create_uid": self.user.display_name,
                    "name": dashboard.name,
                }
            ],
        )
        self.assertEqual(self._get_share_counts(self.user)[dashboard.id], 1)

        share_url = f"/dashboard/share/{own_share.id}/{own_share.access_token}"
        with self.assertRaises(AccessError):
            self._unshare_as(self.user, other_share)

        self.assertTrue(self._unshare_as(self.user, own_share))
        self.assertFalse(self._get_shares(self.user, dashboard))
        self.assertNotIn(dashboard.id, self._get_share_counts(self.user))
        self.assertEqual(self.url_open(share_url).status_code, 404)

    def test_share_flow_of_a_manager(self):
        """A dashboard manager manages the shares of every user."""
        dashboard = self.create_dashboard()
        own_share = self._share_as(self.user, dashboard)
        other_share = self._share_as(self.user2, dashboard)

        self.assertEqual(
            {share["id"] for share in self._get_shares(self.manager, dashboard)},
            {own_share.id, other_share.id},
        )
        self.assertEqual(self._get_share_counts(self.manager)[dashboard.id], 2)

        self.assertTrue(self._unshare_as(self.manager, other_share))
        self.assertFalse(
            self.env["spreadsheet.dashboard.share"].search(
                [("id", "=", other_share.id)]
            )
        )
        self.assertEqual(self._get_share_counts(self.manager)[dashboard.id], 1)
