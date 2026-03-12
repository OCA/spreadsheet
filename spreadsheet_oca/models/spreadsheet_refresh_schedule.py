# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Scheduled data refresh.

Allows users to configure a cron-based schedule that periodically:
  1. Reads all ODOO-type pivot definitions from a spreadsheet's JSON.
  2. Fetches fresh aggregate data via _get_pivot_data().
  3. Posts a Chatter summary on the spreadsheet record and emails
     subscribed partners.

This fills a gap that neither Odoo CE nor Enterprise address:
auto-refresh without a user opening the browser.
"""

import logging

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
    cron_id = fields.Many2one(
        "ir.cron",
        string="Cron Job",
        ondelete="set null",
        readonly=True,
        copy=False,
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

    # ── Cron lifecycle ────────────────────────────────────────────────────────

    def action_activate(self):
        """Create or reactivate the cron job for this schedule."""
        for rec in self:
            if rec.cron_id:
                rec.cron_id.sudo().write(
                    {
                        "active": True,
                        "interval_number": rec.interval_number,
                        "interval_type": rec.interval_type,
                    }
                )
            else:
                model_id = self.env["ir.model"].sudo()._get(self._name).id
                cron = (
                    self.env["ir.cron"]
                    .sudo()
                    .create(
                        {
                            "name": _(
                                "Spreadsheet Refresh: %(name)s",
                                name=rec.spreadsheet_id.name,
                            ),
                            "model_id": model_id,
                            "state": "code",
                            "code": f"model.browse({rec.id})._run_refresh()",
                            "interval_number": rec.interval_number,
                            "interval_type": rec.interval_type,
                            "active": True,
                        }
                    )
                )
                rec.cron_id = cron

    def action_deactivate(self):
        """Pause (deactivate) the cron job without deleting it."""
        for rec in self:
            if rec.cron_id:
                rec.cron_id.sudo().write({"active": False})

    def action_run_now(self):
        """Manually trigger a refresh immediately."""
        self.ensure_one()
        self._run_refresh()

    def unlink(self):
        crons = self.mapped("cron_id").sudo()
        result = super().unlink()
        crons.unlink()
        return result

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

        # Sync input parameters and build substitution dict before processing pivots.
        self.env["spreadsheet.input_param"]._sync_all_for_spreadsheet(spreadsheet.id)
        input_params = self.env["spreadsheet.input_param"].search(
            [
                ("spreadsheet_id", "=", spreadsheet.id),
                ("active", "=", True),
            ]
        )
        param_dict = {p.name: p.current_value or "" for p in input_params}

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
