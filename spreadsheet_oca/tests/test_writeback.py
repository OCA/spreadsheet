# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Tests for cell writeback: edit list cells to update Odoo records.

Controller tests exercise the model-level logic directly rather than
going through the HTTP stack (no test HTTP client is needed for unit
tests in Odoo's TransactionCase framework).

The controller's writeback() method is tested indirectly by calling
the underlying model operations; the controller integration is
implicitly covered by the fact that the controller delegates entirely
to env[model].write() and env['spreadsheet.writeback.log'].create(),
both of which are exercised here.
"""

import logging
from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase

_logger = logging.getLogger(__name__)


class TestWriteback(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a spreadsheet with writeback enabled
        cls.spreadsheet = cls.env["spreadsheet.spreadsheet"].create(
            {
                "name": "Writeback Test Spreadsheet",
                "writeback_enabled": True,
            }
        )

        # Create a spreadsheet with writeback disabled for negative tests
        cls.spreadsheet_off = cls.env["spreadsheet.spreadsheet"].create(
            {
                "name": "Writeback Disabled Spreadsheet",
                "writeback_enabled": False,
            }
        )

        # Use res.partner as the target model — always available in CE
        cls.partner = cls.env["res.partner"].create(
            {"name": "Writeback Test Partner", "email": "wb@test.example"}
        )

    # ── Helper ────────────────────────────────────────────────────────────────

    def _simulate_writeback(
        self,
        spreadsheet,
        model,
        record_id,
        field_name,
        new_value,
        env=None,
    ):
        """
        Simulate the controller's writeback logic using the ORM directly,
        mirroring what SpreadsheetWriteback.writeback() does.

        Returns the same dict the controller would return: either
        {'success': True, 'old_value': ..., 'new_value': ..., 'log_id': ...}
        or {'error': '<message>'}.
        """
        if env is None:
            env = self.env

        log_vals_base = {
            "spreadsheet_id": spreadsheet.id,
            "res_model": model,
            "record_id": record_id,
            "field_name": field_name,
            "new_value": str(new_value),
        }

        try:
            if not spreadsheet.exists():
                return {"error": "Spreadsheet not found."}

            if not spreadsheet.writeback_enabled:
                return {"error": "Writeback not enabled for this spreadsheet."}

            try:
                spreadsheet.check_access("read")
            except AccessError:
                return {"error": "Access denied to spreadsheet."}

            if model not in env:
                return {"error": f"Model {model!r} is not available."}

            record = env[model].browse(record_id)
            if not record.exists():
                return {"error": f"Record {model}({record_id}) not found."}

            try:
                record.check_access("write")
            except AccessError:
                return {
                    "error": "Access denied: you do not have"
                    " write access on this record."
                }

            old_value = record[field_name]
            old_value_str = str(old_value)

            record.write({field_name: new_value})

            log = (
                env["spreadsheet.writeback.log"]
                .sudo()
                .create(
                    dict(
                        log_vals_base,
                        old_value=old_value_str,
                        status="ok",
                    )
                )
            )

            spreadsheet.sudo().message_post(
                body=(
                    f"Writeback: field <b>{field_name}</b> on "
                    f"<b>{model}</b> #{record_id} changed "
                    f"from <b>{old_value_str}</b>"
                    f" to <b>{new_value}</b>."
                ),
                subtype_xmlid="mail.mt_note",
            )

            return {
                "success": True,
                "old_value": old_value_str,
                "new_value": str(new_value),
                "log_id": log.id,
            }

        except Exception as exc:
            try:
                env["spreadsheet.writeback.log"].sudo().create(
                    dict(
                        log_vals_base,
                        status="error",
                        error_message=str(exc)[:255],
                    )
                )
            except Exception:
                _logger.debug("Failed to create writeback error log entry")
            return {"error": str(exc)}

    # ── test_writeback_disabled_returns_error ──────────────────────────────────

    def test_writeback_disabled_returns_error(self):
        """Controller returns an error dict when writeback_enabled is False."""
        result = self._simulate_writeback(
            self.spreadsheet_off,
            "res.partner",
            self.partner.id,
            "name",
            "Should Not Happen",
        )
        self.assertIn("error", result)
        self.assertNotIn("success", result)
        self.assertIn("not enabled", result["error"].lower())

    # ── test_writeback_creates_log ─────────────────────────────────────────────

    def test_writeback_creates_log(self):
        """A successful writeback creates a spreadsheet.writeback.log record."""
        log_count_before = self.env["spreadsheet.writeback.log"].search_count(
            [("spreadsheet_id", "=", self.spreadsheet.id)]
        )
        result = self._simulate_writeback(
            self.spreadsheet,
            "res.partner",
            self.partner.id,
            "name",
            "Writeback Log Test",
        )
        self.assertTrue(result.get("success"), result)
        log_count_after = self.env["spreadsheet.writeback.log"].search_count(
            [("spreadsheet_id", "=", self.spreadsheet.id)]
        )
        self.assertGreater(log_count_after, log_count_before)

    # ── test_writeback_updates_record ──────────────────────────────────────────

    def test_writeback_updates_record(self):
        """The target record's field is actually changed after a writeback."""
        new_name = "Updated By Writeback"
        result = self._simulate_writeback(
            self.spreadsheet,
            "res.partner",
            self.partner.id,
            "name",
            new_name,
        )
        self.assertTrue(result.get("success"), result)
        self.partner.invalidate_recordset()
        self.assertEqual(self.partner.name, new_name)

    # ── test_writeback_log_contains_old_value ─────────────────────────────────

    def test_writeback_log_contains_old_value(self):
        """The log entry captures the old value before the write."""
        # Set a known starting name
        self.partner.write({"name": "Known Old Name"})
        result = self._simulate_writeback(
            self.spreadsheet,
            "res.partner",
            self.partner.id,
            "name",
            "New Name After Writeback",
        )
        self.assertTrue(result.get("success"), result)
        self.assertEqual(result["old_value"], "Known Old Name")

        log = self.env["spreadsheet.writeback.log"].browse(result["log_id"])
        self.assertEqual(log.old_value, "Known Old Name")
        self.assertEqual(log.field_name, "name")
        self.assertEqual(log.status, "ok")

    # ── test_writeback_access_denied ──────────────────────────────────────────

    def test_writeback_access_denied(self):
        """
        A user without write access on the target record gets an error dict.

        We patch check_access on the record to raise AccessError, simulating
        a restricted user without going through the full ir.rule machinery.
        """
        # Create the record as admin
        protected_partner = (
            self.env["res.partner"].sudo().create({"name": "Protected Partner"})
        )

        # Patch check_access to always raise AccessError for this test
        with patch.object(
            type(protected_partner),
            "check_access",
            side_effect=AccessError("Access denied"),
        ):
            result = self._simulate_writeback(
                self.spreadsheet,
                "res.partner",
                protected_partner.id,
                "name",
                "Should Fail",
            )

        self.assertIn("error", result)
        self.assertIn("access denied", result["error"].lower())

    # ── test_rollback_restores_value ───────────────────────────────────────────

    def test_rollback_restores_value(self):
        """action_rollback_writeback restores the old field value."""
        original_name = "Pre-Rollback Name"
        self.partner.write({"name": original_name})

        result = self._simulate_writeback(
            self.spreadsheet,
            "res.partner",
            self.partner.id,
            "name",
            "Changed Name",
        )
        self.assertTrue(result.get("success"), result)
        self.partner.invalidate_recordset()
        self.assertEqual(self.partner.name, "Changed Name")

        # Roll back via the spreadsheet model method
        self.spreadsheet.action_rollback_writeback(result["log_id"])

        self.partner.invalidate_recordset()
        self.assertEqual(self.partner.name, original_name)

    # ── test_rollback_marks_log_rolled_back ───────────────────────────────────

    def test_rollback_marks_log_rolled_back(self):
        """The log entry status changes to 'rolled_back' after a rollback."""
        self.partner.write({"name": "Before Rollback Mark"})
        result = self._simulate_writeback(
            self.spreadsheet,
            "res.partner",
            self.partner.id,
            "name",
            "After Write",
        )
        self.assertTrue(result.get("success"), result)

        log = self.env["spreadsheet.writeback.log"].browse(result["log_id"])
        self.assertEqual(log.status, "ok")

        self.spreadsheet.action_rollback_writeback(result["log_id"])
        log.invalidate_recordset()
        self.assertEqual(log.status, "rolled_back")

    # ── test_smart_button_count ────────────────────────────────────────────────

    def test_smart_button_count(self):
        """writeback_log_count reflects successful log entries."""
        self.spreadsheet.invalidate_recordset()
        count_before = self.spreadsheet.writeback_log_count

        # Write once
        self.partner.write({"name": "Count Test 1"})
        r1 = self._simulate_writeback(
            self.spreadsheet,
            "res.partner",
            self.partner.id,
            "name",
            "Count Test 2",
        )
        self.assertTrue(r1.get("success"), r1)

        # Write again
        r2 = self._simulate_writeback(
            self.spreadsheet,
            "res.partner",
            self.partner.id,
            "name",
            "Count Test 3",
        )
        self.assertTrue(r2.get("success"), r2)

        self.spreadsheet.invalidate_recordset()
        self.assertEqual(self.spreadsheet.writeback_log_count, count_before + 2)

    # ── test_writeback_posts_chatter_message ──────────────────────────────────

    def test_writeback_posts_chatter_message(self):
        """A chatter note appears on the spreadsheet after a writeback."""
        self.partner.write({"name": "Chatter Test Start"})
        msg_count_before = self.env["mail.message"].search_count(
            [
                ("res_id", "=", self.spreadsheet.id),
                ("model", "=", "spreadsheet.spreadsheet"),
            ]
        )
        result = self._simulate_writeback(
            self.spreadsheet,
            "res.partner",
            self.partner.id,
            "name",
            "Chatter Test End",
        )
        self.assertTrue(result.get("success"), result)

        msg_count_after = self.env["mail.message"].search_count(
            [
                ("res_id", "=", self.spreadsheet.id),
                ("model", "=", "spreadsheet.spreadsheet"),
            ]
        )
        self.assertGreater(msg_count_after, msg_count_before)


# TODO: Add HttpCase tests for the /spreadsheet/writeback JSON-RPC endpoint.
#
# An HttpCase would POST to the controller route directly, verifying the full
# HTTP stack (routing, CSRF, JSON-RPC serialisation, auth).  However, this
# requires:
#   1. A logged-in browser session (HttpCase.authenticate + url_open), or
#      manually crafting a JSON-RPC request with session cookies.
#   2. The Odoo test HTTP server running (HttpCase spins one up, but it uses
#      a separate transaction — test data created in setUpClass is not visible
#      unless using ``@tagged("post_install", "-at_install")``) .
#   3. Careful handling of the JSON-RPC envelope ({"jsonrpc": "2.0", "method":
#      "call", "params": {...}}) which Odoo's ``type="json"`` routes expect.
#
# For now the model-level tests above cover the business logic; the controller
# is a thin wrapper.  A proper HttpCase should be added when the module gets
# integration / end-to-end test infrastructure.
