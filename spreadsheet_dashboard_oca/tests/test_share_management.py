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

    def test_list_only_own_shares(self):
        dashboard = self.create_dashboard()
        share_raoul = self._share_as(self.user, dashboard)
        share_bob = self._share_as(self.user2, dashboard)

        shares = (
            self.env["spreadsheet.dashboard.share"]
            .with_user(self.user)
            .action_get_dashboard_shares(dashboard.id)
        )
        self.assertEqual(len(shares), 1)
        self.assertEqual(shares[0]["id"], share_raoul.id)
        self.assertEqual(shares[0]["full_url"], share_raoul.full_url)
        self.assertEqual(shares[0]["name"], dashboard.name)
        self.assertEqual(shares[0]["create_uid"], self.user.display_name)
        self.assertTrue(shares[0]["create_date"])
        self.assertNotEqual(shares[0]["id"], share_bob.id)

    def test_manager_sees_all_shares(self):
        dashboard = self.create_dashboard()
        share_raoul = self._share_as(self.user, dashboard)
        share_bob = self._share_as(self.user2, dashboard)

        shares = (
            self.env["spreadsheet.dashboard.share"]
            .with_user(self.manager)
            .action_get_dashboard_shares(dashboard.id)
        )
        self.assertEqual(
            {share["id"] for share in shares}, {share_raoul.id, share_bob.id}
        )

    def test_unshare_own_share(self):
        dashboard = self.create_dashboard()
        share = self._share_as(self.user, dashboard)

        result = (
            self.env["spreadsheet.dashboard.share"]
            .with_user(self.user)
            .action_unshare([share.id])
        )
        self.assertTrue(result)
        self.assertFalse(
            self.env["spreadsheet.dashboard.share"].search([("id", "=", share.id)])
        )

    def test_cannot_unshare_other_users_share(self):
        dashboard = self.create_dashboard()
        share = self._share_as(self.user2, dashboard)

        with self.assertRaises(AccessError):
            (
                self.env["spreadsheet.dashboard.share"]
                .with_user(self.user)
                .action_unshare([share.id])
            )

    def test_manager_can_unshare_other_users_share(self):
        dashboard = self.create_dashboard()
        share = self._share_as(self.user2, dashboard)

        result = (
            self.env["spreadsheet.dashboard.share"]
            .with_user(self.manager)
            .action_unshare([share.id])
        )
        self.assertTrue(result)
        self.assertFalse(
            self.env["spreadsheet.dashboard.share"].search([("id", "=", share.id)])
        )

    def test_unshared_link_returns_404(self):
        dashboard = self.create_dashboard()
        share = self._share_as(self.user, dashboard)
        access_token = share.access_token
        share.with_user(self.user).action_unshare([share.id])

        response = self.url_open(f"/dashboard/share/{share.id}/{access_token}")
        self.assertEqual(response.status_code, 404)

    def test_share_counts_own_shares_only(self):
        dashboard = self.create_dashboard()
        self._share_as(self.user, dashboard)
        self._share_as(self.user2, dashboard)

        counts = (
            self.env["spreadsheet.dashboard.share"]
            .with_user(self.user)
            .action_get_share_counts()
        )
        self.assertEqual(counts[dashboard.id], 1)

    def test_share_counts_manager_sees_all(self):
        dashboard = self.create_dashboard()
        self._share_as(self.user, dashboard)
        self._share_as(self.user2, dashboard)

        counts = (
            self.env["spreadsheet.dashboard.share"]
            .with_user(self.manager)
            .action_get_share_counts()
        )
        self.assertEqual(counts[dashboard.id], 2)

    def test_share_counts_empty_for_dashboard_without_shares(self):
        dashboard = self.create_dashboard()

        counts = (
            self.env["spreadsheet.dashboard.share"]
            .with_user(self.manager)
            .action_get_share_counts()
        )
        self.assertNotIn(dashboard.id, counts)
