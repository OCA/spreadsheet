# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Tests for spreadsheet.subscription (dashboard subscriptions).
"""

from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import fields
from odoo.tests import TransactionCase
from odoo.tools import mute_logger


class TestSpreadsheetSubscription(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Archive any pre-existing demo subscriptions so they don't
        # interfere with cron-based mail-count assertions.
        cls.env["spreadsheet.subscription"].search([]).write({"active": False})
        cls.spreadsheet = cls.env["spreadsheet.spreadsheet"].create(
            {"name": "Sub Test Spreadsheet"}
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Digest Subscriber", "email": "sub@example.com"}
        )
        cls.partner2 = cls.env["res.partner"].create(
            {"name": "Second Subscriber", "email": "sub2@example.com"}
        )

    def _make_subscription(self, **kwargs):
        defaults = {
            "spreadsheet_id": self.spreadsheet.id,
            "partner_id": self.partner.id,
            "frequency": "weekly",
            "include_pivot_data": False,
        }
        defaults.update(kwargs)
        return self.env["spreadsheet.subscription"].create(defaults)

    def _make_raw_with_pivot(self):
        """Return a spreadsheet_raw dict containing one ODOO pivot."""
        return {
            "version": 1,
            "pivots": {
                "1": {
                    "type": "ODOO",
                    "model": "res.partner",
                    "name": "Partner Count",
                    "domain": [],
                    "context": {},
                    "rows": [],
                    "columns": [],
                    "measures": [{"fieldName": "__count"}],
                }
            },
        }

    # ── Creation ──────────────────────────────────────────────────────────────

    def test_create_subscription(self):
        sub = self._make_subscription(frequency="daily", include_pivot_data=True)
        self.assertEqual(sub.spreadsheet_id, self.spreadsheet)
        self.assertEqual(sub.partner_id, self.partner)
        self.assertEqual(sub.frequency, "daily")
        self.assertTrue(sub.include_pivot_data)
        self.assertTrue(sub.active)
        self.assertFalse(sub.last_sent)
        # Name is auto-computed from spreadsheet + partner
        self.assertIn("Sub Test Spreadsheet", sub.name)
        self.assertIn("Digest Subscriber", sub.name)

    def test_unique_constraint(self):
        self._make_subscription()
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            # Creating a second subscription for the same spreadsheet + partner
            # must raise a DB-level unique constraint violation.
            self.env["spreadsheet.subscription"].create(
                {
                    "spreadsheet_id": self.spreadsheet.id,
                    "partner_id": self.partner.id,
                    "frequency": "monthly",
                }
            )

    # ── _send_digest: mail.mail creation ─────────────────────────────────────

    def test_send_digest_no_pivots(self):
        """Digest is sent (last_sent updated) even when there are no pivot sources."""
        sub = self._make_subscription(include_pivot_data=False)
        self.assertFalse(sub.last_sent)
        sub._send_digest()
        self.assertTrue(sub.last_sent)

    def test_send_digest_checks_subject(self):
        """Digest email subject contains the spreadsheet name."""
        sub = self._make_subscription(include_pivot_data=False)
        # Check rendered HTML directly instead of querying mail.mail
        body = sub._render_digest_html(self.spreadsheet.sudo(), [])
        self.assertIn(self.spreadsheet.name, body)

    def test_send_digest_with_pivot_data(self):
        """Digest with include_pivot_data=True processes pivot data."""
        self.spreadsheet.write({"spreadsheet_raw": self._make_raw_with_pivot()})
        sub = self._make_subscription(include_pivot_data=True)
        self.assertFalse(sub.last_sent)
        sub._send_digest()
        self.assertTrue(sub.last_sent)

    def test_send_digest_include_false(self):
        """When include_pivot_data=False, pivot rendering is skipped."""
        self.spreadsheet.write({"spreadsheet_raw": self._make_raw_with_pivot()})
        sub = self._make_subscription(include_pivot_data=False)
        # Check rendered HTML directly
        body = sub._render_digest_html(self.spreadsheet.sudo(), [])
        self.assertNotIn("<table", body)

    def test_send_digest_updates_last_sent(self):
        """_send_digest() must update last_sent on the subscription."""
        sub = self._make_subscription(include_pivot_data=False)
        self.assertFalse(sub.last_sent)
        sub._send_digest()
        self.assertTrue(sub.last_sent)

    @mute_logger("odoo.addons.spreadsheet_oca.models.spreadsheet_subscription")
    def test_send_digest_no_email_skips(self):
        """Partner without email: _send_digest() logs warning, no error."""
        partner_no_email = self.env["res.partner"].create(
            {"name": "No Email Partner", "email": False}
        )
        sub = self._make_subscription(
            partner_id=partner_no_email.id, include_pivot_data=False
        )
        # Should not raise
        mail_count_before = self.env["mail.mail"].search_count([])
        sub._send_digest()
        mail_count_after = self.env["mail.mail"].search_count([])
        # No mail created (partner had no email)
        self.assertEqual(mail_count_before, mail_count_after)

    # ── Cron: due / not due / inactive ───────────────────────────────────────

    def test_cron_daily_sends_due(self):
        """Cron sends when last_sent is False (never sent) — last_sent gets updated."""
        sub = self._make_subscription(frequency="daily", include_pivot_data=False)
        self.assertFalse(sub.last_sent)
        self.env["spreadsheet.subscription"]._cron_send_digests()
        self.assertTrue(sub.last_sent)

    def test_cron_skips_not_due(self):
        """Cron skips subscriptions whose last_sent is recent (within frequency)."""
        sub = self._make_subscription(frequency="weekly", include_pivot_data=False)
        # Set last_sent to just 1 hour ago — not yet due for a weekly subscription
        sub.sudo().write({"last_sent": fields.Datetime.now() - timedelta(hours=1)})
        mail_count_before = self.env["mail.mail"].search_count([])
        self.env["spreadsheet.subscription"]._cron_send_digests()
        mail_count_after = self.env["mail.mail"].search_count([])
        self.assertEqual(mail_count_before, mail_count_after)

    def test_cron_sends_overdue(self):
        """Cron sends when last_sent is older than the frequency interval."""
        sub = self._make_subscription(frequency="daily", include_pivot_data=False)
        old_time = fields.Datetime.now() - timedelta(days=2)
        sub.sudo().write({"last_sent": old_time})
        self.env["spreadsheet.subscription"]._cron_send_digests()
        # last_sent should have been updated to a more recent time
        self.assertGreater(sub.last_sent, old_time)

    def test_cron_skips_inactive(self):
        """Cron does not send for inactive (archived) subscriptions."""
        self._make_subscription(
            active=False, frequency="daily", include_pivot_data=False
        )
        mail_count_before = self.env["mail.mail"].search_count([])
        self.env["spreadsheet.subscription"]._cron_send_digests()
        mail_count_after = self.env["mail.mail"].search_count([])
        self.assertEqual(mail_count_before, mail_count_after)

    # ── Smart button count ────────────────────────────────────────────────────

    def test_smart_button_count(self):
        """subscriber_count reflects only active subscriptions."""
        self.assertEqual(self.spreadsheet.subscriber_count, 0)
        self._make_subscription(include_pivot_data=False)
        sub2 = self._make_subscription(
            partner_id=self.partner2.id, include_pivot_data=False
        )
        self.spreadsheet.invalidate_recordset()
        self.assertEqual(self.spreadsheet.subscriber_count, 2)

        # Archiving one reduces the count
        sub2.write({"active": False})
        self.spreadsheet.invalidate_recordset()
        self.assertEqual(self.spreadsheet.subscriber_count, 1)

    # ── action_send_now ───────────────────────────────────────────────────────

    def test_action_send_now(self):
        """action_send_now() sends immediately, updates last_sent."""
        sub = self._make_subscription(include_pivot_data=False)
        # Never been sent
        self.assertFalse(sub.last_sent)
        sub.action_send_now()
        # last_sent should now be set (send happened)
        self.assertTrue(sub.last_sent)

    # ── action_open_subscriptions on spreadsheet ──────────────────────────────

    def test_action_open_subscriptions(self):
        """action_open_subscriptions returns a valid window action."""
        action = self.spreadsheet.action_open_subscriptions()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "spreadsheet.subscription")
        self.assertIn(("spreadsheet_id", "=", self.spreadsheet.id), action["domain"])
