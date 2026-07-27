# Copyright 2026 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Scheduled data refresh.

Allows users to configure a cron-based schedule that periodically:
  1. Reads all ODOO-type pivot definitions from a spreadsheet's JSON.
  2. Fetches fresh aggregate data via get_pivot_data().
  3. Posts a Chatter summary on the spreadsheet record and emails
     subscribed partners.

This fills a gap that neither Odoo CE nor Enterprise address:
auto-refresh without a user opening the browser.
"""

import logging

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .pivot_data import collect_pivot_summaries, render_pivot_table_html

_logger = logging.getLogger(__name__)


def _apply_param_substitution(domain, params):
    """
    Replace ``%(name)s`` tokens in string leaf values of an Odoo domain list.

    Only the *value* position (index 2) of ``(field, operator, value)`` tuples
    is touched — field names and operators are never modified.  Nested domain
    lists (e.g. ``["&", cond1, cond2]``) are handled recursively.

    *params* is a ``{name: value}`` dict (values are already strings).
    Safe: substituted values come from the DB, not from user input at runtime.

    Example::

        domain = [("date", ">=", "%(start_date)s")]
        params = {"start_date": "2026-01-01"}
        → [("date", ">=", "2026-01-01")]
    """
    if not isinstance(domain, list):
        return domain
    result = []
    for item in domain:
        if isinstance(item, tuple | list) and len(item) == 3:
            field, op, value = item
            if isinstance(value, str):
                try:
                    value = value % params
                except KeyError as exc:
                    _logger.warning(
                        "Domain substitution: unknown param %s — token left as-is", exc
                    )
                except TypeError:
                    _logger.debug(
                        "Domain substitution: value %r has lone %%",
                        value,
                    )
            result.append((field, op, value))
        elif isinstance(item, list):
            result.append(_apply_param_substitution(item, params))
        else:
            result.append(item)
    return result


_INTERVAL_TYPES = [
    ("hours", "Hour(s)"),
    ("days", "Day(s)"),
    ("weeks", "Week(s)"),
    ("months", "Month(s)"),
]


class SpreadsheetRefreshSchedule(models.Model):
    _name = "spreadsheet.refresh.schedule"
    _description = "Spreadsheet Scheduled Data Refresh"
    _inherit = ["mail.thread"]
    _order = "spreadsheet_id, name"

    name = fields.Char(required=True, tracking=True)
    spreadsheet_id = fields.Many2one(
        "spreadsheet.spreadsheet",
        required=True,
        ondelete="cascade",
        index=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    user_id = fields.Many2one(
        "res.users",
        string="Run As",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        help="The refresh is computed with this user's permissions, so a "
        "summary never contains records they could not read themselves.",
    )
    last_run = fields.Datetime(readonly=True, copy=False)
    notify_partner_ids = fields.Many2many(
        "res.partner",
        string="Notify Partners",
        help="These partners receive an email summary after each refresh.",
    )
    interval_number = fields.Integer(
        default=1,
        string="Every",
        tracking=True,
    )
    interval_type = fields.Selection(
        _INTERVAL_TYPES,
        default="weeks",
        string="Interval",
        tracking=True,
        required=True,
    )

    @api.constrains("interval_number")
    def _check_interval_number(self):
        for rec in self:
            if rec.interval_number < 1:
                raise ValidationError(_("Interval must be at least 1."))

    # ── Scheduling ───────────────────────────────────────────────────────────

    def action_activate(self):
        """Resume this schedule."""
        self.write({"active": True})

    def action_deactivate(self):
        """Pause this schedule without losing its configuration."""
        self.write({"active": False})

    def action_run_now(self):
        """Manually trigger a refresh immediately."""
        self.ensure_one()
        self._run_refresh()

    def _next_run(self):
        """Return when this schedule is next due, or None if it never ran."""
        self.ensure_one()
        if not self.last_run:
            return None
        return self.last_run + relativedelta(
            **{self.interval_type: self.interval_number}
        )

    def _is_due(self, now):
        """A schedule that has never run is due immediately."""
        self.ensure_one()
        next_run = self._next_run()
        return next_run is None or next_run <= now

    @api.model
    def _cron_run_due(self):
        """Called by the shared ir.cron: refresh every schedule that is due.

        Each schedule runs as its own ``user_id`` rather than as the cron's
        user, so the computed summary can only ever contain records that user
        is allowed to read.  One failing schedule must not stop the others.
        """
        now = fields.Datetime.now()
        for schedule in self.search([("active", "=", True)]):
            if not schedule._is_due(now):
                continue
            try:
                schedule.with_user(schedule.user_id)._run_refresh()
            except Exception:
                _logger.exception(
                    "Scheduled refresh failed for schedule %s (%s)",
                    schedule.id,
                    schedule.name,
                )

    def _get_param_dict(self, spreadsheet):
        """Return ``{name: value}`` dict for domain-template substitution.

        Default implementation returns an empty dict.  The ``input_params``
        feature overrides this to sync named parameters from the spreadsheet
        and return their current values.
        """
        return {}

    # ── Refresh execution ────────────────────────────────────────────────────

    def _run_refresh(self):
        """
        Execute one refresh cycle:
          - Read pivot definitions from spreadsheet_raw JSON.
          - Compute fresh data for each ODOO pivot.
          - Post Chatter summary; email notify_partner_ids.
          - Record last_run timestamp.
        """
        self.ensure_one()
        spreadsheet = self.spreadsheet_id

        param_dict = self._get_param_dict(spreadsheet)

        raw = spreadsheet.sudo().spreadsheet_raw or {}

        if not raw.get("pivots"):
            _logger.info(
                "Spreadsheet refresh %s: no pivots found in spreadsheet %s",
                self.id,
                spreadsheet.id,
            )
            self.sudo().write({"last_run": fields.Datetime.now()})
            return

        summaries, failed_pivot_names = collect_pivot_summaries(
            self.env,
            raw,
            domain_transform=lambda d: _apply_param_substitution(d, param_dict),
        )

        body = self._render_refresh_html(summaries)
        partner_ids = self.notify_partner_ids.ids

        spreadsheet.sudo().message_post(
            body=body,
            subject=_("Data refresh: %(name)s", name=spreadsheet.name),
            partner_ids=partner_ids,
            subtype_xmlid="mail.mt_comment" if partner_ids else "mail.mt_note",
        )

        if failed_pivot_names:
            warning_body = self.env["ir.qweb"]._render(
                "spreadsheet_oca.spreadsheet_refresh_warning_template",
                {
                    "schedule_name": self.name,
                    "failed_names": failed_pivot_names,
                },
            )
            spreadsheet.sudo().message_post(
                body=warning_body,
                subtype_xmlid="mail.mt_note",
            )

        self.sudo().write({"last_run": fields.Datetime.now()})

    # ── HTML rendering ────────────────────────────────────────────────────────

    @api.model
    def _render_refresh_html(self, summaries):
        """Render a compact HTML summary of fresh pivot data.

        Uses the QWeb template ``spreadsheet_refresh_notification_template``
        which can be customised via Settings > Technical > Views.
        """
        pivot_html_list = [Markup(render_pivot_table_html(s)) for s in summaries]
        return self.env["ir.qweb"]._render(
            "spreadsheet_oca.spreadsheet_refresh_notification_template",
            {"pivot_html_list": pivot_html_list},
        )
