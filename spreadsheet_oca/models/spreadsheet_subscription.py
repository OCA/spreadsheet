# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Dashboard subscriptions.

Allows partners to subscribe to a periodic email digest of a spreadsheet.
A shared daily cron evaluates all active subscriptions and sends those that
are due (based on frequency and last_sent timestamp).

Each digest email optionally includes a compact pivot data summary rendered
with inline CSS, suitable for email clients.
"""

import logging
from datetime import timedelta

from markupsafe import Markup

from odoo import _, api, fields, models

from .pivot_data import collect_pivot_summaries, render_pivot_table_html

_logger = logging.getLogger(__name__)

_FREQUENCY_SELECTION = [
    ("daily", "Daily"),
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
]

_FREQUENCY_DELTA = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "monthly": timedelta(days=30),
}


class SpreadsheetSubscription(models.Model):
    _name = "spreadsheet.subscription"
    _description = "Spreadsheet Dashboard Subscription"
    _inherit = ["mail.thread"]
    _order = "spreadsheet_id, partner_id"

    name = fields.Char(
        compute="_compute_name",
        store=True,
        readonly=False,
    )
    spreadsheet_id = fields.Many2one(
        "spreadsheet.spreadsheet",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Subscriber",
        required=True,
        ondelete="restrict",
        index=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    user_id = fields.Many2one(
        "res.users",
        string="Run As",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        help="The digest is computed with this user's permissions, so a "
        "subscriber never receives figures this user could not read.",
    )
    frequency = fields.Selection(
        _FREQUENCY_SELECTION,
        default="weekly",
        required=True,
        tracking=True,
    )
    last_sent = fields.Datetime(readonly=True, copy=False)
    include_pivot_data = fields.Boolean(
        default=True,
        help="Include a live pivot data summary in the email.",
    )

    _sql_constraints = [
        (
            "unique_spreadsheet_partner",
            "UNIQUE(spreadsheet_id, partner_id)",
            "A partner can only have one subscription per spreadsheet.",
        ),
    ]

    # ── Default name computation ───────────────────────────────────────────────

    @api.depends("spreadsheet_id", "partner_id")
    def _compute_name(self):
        for rec in self:
            spreadsheet_name = rec.spreadsheet_id.name or _("Unnamed Spreadsheet")
            partner_name = rec.partner_id.name or _("Unknown Partner")
            rec.name = f"{spreadsheet_name} — {partner_name}"

    # ── Shared cron ───────────────────────────────────────────────────────────

    @api.model
    def _cron_send_digests(self):
        """Called by the shared ir.cron: send digests that are due."""
        active_subs = self.search([("active", "=", True)])
        now = fields.Datetime.now()
        for sub in active_subs:
            try:
                sub.with_user(sub.user_id)._send_digest_if_due(now)
            except Exception:
                _logger.exception(
                    "Failed to send digest for subscription %s (%s)",
                    sub.id,
                    sub.name,
                )

    def _send_digest_if_due(self, now=None):
        """Send this subscription's digest if it is due, otherwise skip."""
        self.ensure_one()
        if now is None:
            now = fields.Datetime.now()
        delta = _FREQUENCY_DELTA.get(self.frequency, timedelta(weeks=1))
        if self.last_sent and (now - self.last_sent) < delta:
            return  # not due yet
        self._send_digest()

    # ── Digest sending ────────────────────────────────────────────────────────

    def _send_digest(self):
        """Generate and send a digest email for this subscription."""
        self.ensure_one()
        spreadsheet = self.spreadsheet_id.sudo()
        summaries = []

        if self.include_pivot_data:
            raw = spreadsheet.spreadsheet_raw or {}
            summaries, _failed = collect_pivot_summaries(self.env, raw)

        body_html = self._render_digest_html(spreadsheet, summaries)
        subject = _("Spreadsheet Digest: %(name)s", name=spreadsheet.name)

        partner = self.partner_id
        email_to = partner.email
        if not email_to:
            _logger.warning(
                "Subscription %s: partner %s has no email — skipping",
                self.id,
                partner.name,
            )
            return

        # An explicit sender: without one the mail only goes out if the server
        # happens to have mail.catchall.domain / mail.default.from configured,
        # and mail.mail logs the failure rather than raising it.
        email_from = (
            self.user_id.email_formatted
            or self.env.company.email_formatted
            or self.env.company.email
        )
        if not email_from:
            _logger.warning(
                "Subscription %s: no sender address available (neither %s nor "
                "the company has an email) — digest not sent",
                self.id,
                self.user_id.name,
            )
            return

        self.env["mail.mail"].sudo().create(
            {
                "subject": subject,
                "body_html": body_html,
                "email_to": email_to,
                "email_from": email_from,
            }
        ).send()

        self.sudo().write({"last_sent": fields.Datetime.now()})

    # ── HTML rendering ────────────────────────────────────────────────────────

    def _render_digest_html(self, spreadsheet, summaries):
        """Return a styled HTML email body for the digest.

        Uses the QWeb template ``spreadsheet_subscription_digest_template``
        which can be customised via Settings > Technical > Views.

        Args:
            spreadsheet: browse record of spreadsheet.spreadsheet (already sudo'd).
            summaries:   list of {"name", "model", "result"} dicts from _get_pivot_data.

        Returns:
            str — complete HTML body suitable for sending via mail.mail.
        """
        now_str = fields.Datetime.now().strftime("%Y-%m-%d %H:%M UTC")
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        pivot_html_list = [Markup(render_pivot_table_html(s)) for s in summaries]
        return self.env["ir.qweb"]._render(
            "spreadsheet_oca.spreadsheet_subscription_digest_template",
            {
                "spreadsheet": spreadsheet,
                "now_str": now_str,
                "summaries": summaries,
                "pivot_html_list": pivot_html_list,
                "base_url": base_url,
            },
        )

    # ── Manual send ───────────────────────────────────────────────────────────

    def action_send_now(self):
        """Manually send the digest immediately, bypassing the due check."""
        self.ensure_one()
        self._send_digest()
