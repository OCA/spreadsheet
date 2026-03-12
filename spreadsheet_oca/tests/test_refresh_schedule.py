# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Tests for spreadsheet.refresh.schedule (scheduled cron refresh).

These tests verify:
  - Schedule creation and cron lifecycle (activate / deactivate / run now).
  - _run_refresh() correctly reads pivot defs from spreadsheet_raw,
    calls _get_pivot_data(), and posts a Chatter message.
  - Graceful handling of edge cases (no pivots, unknown model).
  - HTML renderer produces non-empty output.
  - Smart button count on spreadsheet.spreadsheet.

Run:
  docker exec -i odoo-prod odoo test -d odoo_test \\
    --test-tags spreadsheet_oca.TestRefreshSchedule --stop-after-init
"""

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
        self.assertFalse(schedule.cron_id)
        self.assertFalse(schedule.last_run)

    def test_activate_creates_cron(self):
        schedule = self._make_schedule()
        schedule.action_activate()
        self.assertTrue(schedule.cron_id)
        self.assertTrue(schedule.cron_id.active)
        self.assertEqual(schedule.cron_id.interval_number, 1)
        self.assertEqual(schedule.cron_id.interval_type, "weeks")

    def test_activate_twice_reuses_cron(self):
        schedule = self._make_schedule()
        schedule.action_activate()
        cron_id_first = schedule.cron_id.id
        schedule.action_deactivate()
        schedule.action_activate()
        self.assertEqual(schedule.cron_id.id, cron_id_first)

    def test_deactivate_pauses_cron(self):
        schedule = self._make_schedule()
        schedule.action_activate()
        schedule.action_deactivate()
        self.assertFalse(schedule.cron_id.active)

    def test_unlink_removes_cron(self):
        schedule = self._make_schedule()
        schedule.action_activate()
        cron = schedule.cron_id
        schedule.unlink()
        self.assertFalse(cron.exists())

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
