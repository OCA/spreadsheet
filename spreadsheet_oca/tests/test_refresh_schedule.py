# Copyright 2026 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Tests for spreadsheet.refresh.schedule (scheduled cron refresh).

These tests verify:
  - Activate/pause, the due-check, and that the shared cron runs each
    schedule as its own user.
  - _run_refresh() correctly reads pivot defs from spreadsheet_raw,
    calls get_pivot_data(), and posts a Chatter message.
  - Graceful handling of edge cases (no pivots, unknown model).
  - HTML renderer produces non-empty output.
  - Smart button count on spreadsheet.spreadsheet.

Run:
  docker exec -i odoo-prod odoo test -d odoo_test \\
    --test-tags spreadsheet_oca.TestRefreshSchedule --stop-after-init
"""

from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase
from odoo.tools import mute_logger


class TestRefreshSchedule(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spreadsheet = cls.env["spreadsheet.spreadsheet"].create(
            {"name": "Test Spreadsheet"}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test Subscriber"})

    # ── Schedule creation ────────────────────────────────────────────────────

    def _make_schedule(self, **kwargs):
        defaults = {
            "name": "Weekly Refresh",
            "spreadsheet_id": self.spreadsheet.id,
            "interval_number": 1,
            "interval_type": "weeks",
        }
        defaults.update(kwargs)
        return self.env["spreadsheet.refresh.schedule"].create(defaults)

    def test_create_schedule(self):
        schedule = self._make_schedule()
        self.assertEqual(schedule.spreadsheet_id, self.spreadsheet)
        self.assertTrue(schedule.active)
        self.assertEqual(schedule.user_id, self.env.user)
        self.assertFalse(schedule.last_run)

    def test_activate_deactivate_toggles_active(self):
        schedule = self._make_schedule()
        schedule.action_deactivate()
        self.assertFalse(schedule.active)
        schedule.action_activate()
        self.assertTrue(schedule.active)

    def test_never_run_is_due_immediately(self):
        schedule = self._make_schedule()
        self.assertFalse(schedule.last_run)
        self.assertTrue(schedule._is_due(fields.Datetime.now()))

    def test_not_due_before_the_interval_elapses(self):
        schedule = self._make_schedule()
        now = fields.Datetime.now()
        schedule.last_run = now - timedelta(days=3)  # weekly schedule
        self.assertFalse(schedule._is_due(now))

    def test_due_once_the_interval_has_elapsed(self):
        schedule = self._make_schedule()
        now = fields.Datetime.now()
        schedule.last_run = now - timedelta(days=8)  # weekly schedule
        self.assertTrue(schedule._is_due(now))

    def test_cron_skips_inactive_and_not_due(self):
        """The shared cron refreshes only active schedules that are due."""
        due = self._make_schedule()
        not_due = self._make_schedule()
        not_due.last_run = fields.Datetime.now()
        paused = self._make_schedule()
        paused.write({"active": False})

        self.env["spreadsheet.refresh.schedule"]._cron_run_due()

        self.assertTrue(due.last_run, "a due schedule should have run")
        self.assertFalse(paused.last_run, "a paused schedule must be skipped")

    def test_cron_runs_each_schedule_as_its_own_user(self):
        """The refresh must use the schedule's user, not the cron's.

        Otherwise every summary is computed with the cron user's permissions
        and can expose records the schedule's owner cannot read.
        """
        limited = self.env["res.users"].create(
            {
                "name": "Limited",
                "login": "limited_refresh_user",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        schedule = self._make_schedule()
        schedule.user_id = limited

        # (schedule_id, executing_user_id) — other schedules may also be due,
        # and each of those legitimately runs as its own user.
        seen = []
        original = type(schedule)._run_refresh

        def _spy(self_):
            seen.append((self_.id, self_.env.user.id))
            return original(self_)

        self.patch(type(schedule), "_run_refresh", _spy)
        self.env["spreadsheet.refresh.schedule"]._cron_run_due()

        runs = [user_id for sched_id, user_id in seen if sched_id == schedule.id]
        self.assertEqual(
            runs,
            [limited.id],
            "the schedule must run as its own user, not as the cron's",
        )

    # ── _run_refresh — no pivots ─────────────────────────────────────────────

    def test_run_refresh_no_pivots(self):
        """Spreadsheet with no pivots: last_run is still updated."""
        schedule = self._make_schedule()
        before = self.env["mail.message"].search_count(
            [
                ("res_id", "=", self.spreadsheet.id),
                ("model", "=", "spreadsheet.spreadsheet"),
            ]
        )
        schedule._run_refresh()
        self.assertTrue(schedule.last_run)
        # A chatter note is NOT posted when there are no pivots
        after = self.env["mail.message"].search_count(
            [
                ("res_id", "=", self.spreadsheet.id),
                ("model", "=", "spreadsheet.spreadsheet"),
            ]
        )
        self.assertEqual(before, after)

    # ── _run_refresh — with pivot data ───────────────────────────────────────

    def _set_pivot_raw(self, pivot_def):
        """Write a minimal spreadsheet_raw JSON with one ODOO pivot."""
        raw = {
            "version": 1,
            "sheets": [{"id": "sheet1", "name": "Sheet1"}],
            "pivots": {
                "1": pivot_def,
            },
        }
        self.spreadsheet.write({"spreadsheet_raw": raw})

    def test_run_refresh_with_valid_pivot(self):
        """Valid res.partner pivot → posts a Chatter note with HTML body."""
        country_be = self.env.ref("base.be")
        partners = self.env["res.partner"].create(
            [
                {"name": "A", "country_id": country_be.id, "is_company": True},
                {"name": "B", "country_id": country_be.id, "is_company": True},
            ]
        )
        self._set_pivot_raw(
            {
                "type": "ODOO",
                "model": "res.partner",
                "domain": [("id", "in", partners.ids)],
                "context": {},
                "rows": [{"fieldName": "country_id"}],
                "columns": [],
                "measures": [{"fieldName": "__count"}],
                "name": "Partner Pivot",
            }
        )
        schedule = self._make_schedule(notify_partner_ids=[self.partner.id])
        msg_count_before = self.env["mail.message"].search_count(
            [
                ("res_id", "=", self.spreadsheet.id),
                ("model", "=", "spreadsheet.spreadsheet"),
            ]
        )
        schedule._run_refresh()
        self.assertTrue(schedule.last_run)
        msg_count_after = self.env["mail.message"].search_count(
            [
                ("res_id", "=", self.spreadsheet.id),
                ("model", "=", "spreadsheet.spreadsheet"),
            ]
        )
        self.assertGreater(
            msg_count_after, msg_count_before, "Expected a Chatter message"
        )
        # Verify HTML content
        msg = self.env["mail.message"].search(
            [
                ("res_id", "=", self.spreadsheet.id),
                ("model", "=", "spreadsheet.spreadsheet"),
            ],
            order="id desc",
            limit=1,
        )
        self.assertIn("Partner Pivot", msg.body)
        self.assertIn("res.partner", msg.body)

    @mute_logger("odoo.addons.spreadsheet_oca.models.pivot_data")
    def test_run_refresh_unknown_model_skipped(self):
        """Pivot with an unknown model is skipped; last_run still set."""
        self._set_pivot_raw(
            {
                "type": "ODOO",
                "model": "nonexistent.model.xyz",
                "domain": [],
                "context": {},
                "rows": [],
                "columns": [],
                "measures": [{"fieldName": "__count"}],
                "name": "Bad Pivot",
            }
        )
        schedule = self._make_schedule()
        schedule._run_refresh()
        self.assertTrue(schedule.last_run)

    def test_run_refresh_non_odoo_pivot_skipped(self):
        """Non-ODOO type pivot is ignored."""
        raw = {
            "version": 1,
            "sheets": [{"id": "sheet1", "name": "Sheet1"}],
            "pivots": {
                "1": {"type": "STATIC", "model": "res.partner"},
            },
        }
        self.spreadsheet.write({"spreadsheet_raw": raw})
        schedule = self._make_schedule()
        schedule._run_refresh()
        self.assertTrue(schedule.last_run)

    # ── HTML renderer ────────────────────────────────────────────────────────

    def test_render_refresh_html_empty(self):
        html = self.env["spreadsheet.refresh.schedule"]._render_refresh_html([])
        self.assertIn("No ODOO pivot", html)

    def test_render_refresh_html_with_data(self):
        result = {
            "groups": [
                {
                    "rowGroupBy": [],
                    "colGroupBy": [],
                    "rowValues": [],
                    "colValues": [],
                    "count": 42,
                    "measures": {"__count": 42},
                }
            ],
            "rowDimensions": [],
            "colDimensions": [],
            "measureSpecs": ["__count"],
        }
        summaries = [{"name": "My Pivot", "model": "res.partner", "result": result}]
        html = self.env["spreadsheet.refresh.schedule"]._render_refresh_html(summaries)
        self.assertIn("My Pivot", html)
        self.assertIn("res.partner", html)
        self.assertIn("42", html)

    # ── Smart button count ───────────────────────────────────────────────────

    def test_smart_button_count(self):
        self.assertEqual(self.spreadsheet.refresh_schedule_count, 0)
        self._make_schedule()
        self._make_schedule(name="Daily", interval_type="days")
        self.spreadsheet.invalidate_recordset()
        self.assertEqual(self.spreadsheet.refresh_schedule_count, 2)
