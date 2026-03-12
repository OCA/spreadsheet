# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Threshold alerts / KPI watches.

Users define a watch on a named cell in a spreadsheet. A shared cron
periodically evaluates the cell's current value (computed server-side
by calling _get_pivot_data for the first matching pivot at that cell,
or by reading the static value from spreadsheet_raw) and fires a
Discuss/email notification when the threshold is crossed.

Two trigger modes:
  edge  — notify only on the first evaluation that crosses the threshold
           (stays silent until the condition resets and re-triggers)
  level — notify on every cron cycle where the condition holds

Operators: >, >=, <, <=, ==, !=
"""

import logging
import operator as _op

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .cell_ref import parse_cell_ref, read_cell_value

_logger = logging.getLogger(__name__)

_OPERATORS = [
    (">", "> (greater than)"),
    (">=", ">= (greater or equal)"),
    ("<", "< (less than)"),
    ("<=", "<= (less or equal)"),
    ("==", "== (equal to)"),
    ("!=", "!= (not equal to)"),
]

_TRIGGER_MODES = [
    ("edge", "Edge — notify once when threshold is first crossed"),
    ("level", "Level — notify every cycle the condition holds"),
]

# Maps operator selection values to Python comparison callables.
_OP_FUNCS = {
    ">": _op.gt,
    ">=": _op.ge,
    "<": _op.lt,
    "<=": _op.le,
    "==": _op.eq,
    "!=": _op.ne,
}


class SpreadsheetAlert(models.Model):
    _name = "spreadsheet.alert"
    _description = "Spreadsheet KPI Threshold Alert"
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

    # ── Cell reference ────────────────────────────────────────────────────────
    sheet_name = fields.Char(
        help="Sheet containing the watched cell (blank = first sheet).",
    )
    cell_ref = fields.Char(
        string="Cell Reference",
        required=True,
        help="Spreadsheet cell reference, e.g. B3 or D12.",
        tracking=True,
    )

    # ── Threshold ────────────────────────────────────────────────────────────
    operator = fields.Selection(
        _OPERATORS,
        required=True,
        default=">",
        tracking=True,
    )
    threshold = fields.Float(required=True, tracking=True)

    # ── Trigger mode ─────────────────────────────────────────────────────────
    trigger_mode = fields.Selection(
        _TRIGGER_MODES,
        default="edge",
        required=True,
        tracking=True,
        help=(
            "Edge: notify once when the condition changes from False to True. "
            "Level: notify every cron cycle the condition is True."
        ),
    )
    last_state = fields.Boolean(
        default=False,
        readonly=True,
        copy=False,
        help="Previous evaluation state (used for edge mode).",
    )
    last_value = fields.Float(readonly=True, copy=False)
    last_checked = fields.Datetime(readonly=True, copy=False)

    # ── Notification ─────────────────────────────────────────────────────────
    notify_partner_ids = fields.Many2many(
        "res.partner",
        string="Notify Partners",
        help="Notified by email when the threshold is crossed.",
    )

    @api.constrains("cell_ref")
    def _check_cell_ref(self):
        for rec in self:
            col, _row = parse_cell_ref(rec.cell_ref.strip())
            if col is None:
                raise ValidationError(
                    _(
                        "Cell reference %(cell_ref)s must be in the form"
                        " 'A1', 'B12', etc.",
                        cell_ref=rec.cell_ref,
                    )
                )

    # ── Shared cron ───────────────────────────────────────────────────────────

    @api.model
    def _cron_evaluate_all(self):
        """Called by the shared ir.cron: evaluate all active alerts."""
        alerts = self.search([("active", "=", True)])
        for alert in alerts:
            try:
                alert._evaluate()
            except Exception:
                _logger.exception(
                    "Failed to evaluate alert %s (%s)", alert.id, alert.name
                )

    # ── Single alert evaluation ───────────────────────────────────────────────

    def _evaluate(self):
        """
        Evaluate this alert's cell value and fire a notification if the
        threshold condition is met (subject to trigger_mode).
        """
        self.ensure_one()
        value = self._read_cell_value()
        if value is None:
            _logger.debug(
                "Alert %s: cell %s not found or non-numeric", self.id, self.cell_ref
            )
            self.write({"last_checked": fields.Datetime.now()})
            return

        condition_met = self._check_condition(value)
        now = fields.Datetime.now()

        should_notify = False
        if self.trigger_mode == "level":
            should_notify = condition_met
        else:  # edge
            should_notify = condition_met and not self.last_state

        if should_notify:
            self._fire_notification(value)

        self.write(
            {
                "last_state": condition_met,
                "last_value": value,
                "last_checked": now,
            }
        )

    def _check_condition(self, value):
        """Return True if value satisfies operator(value, threshold)."""
        func = _OP_FUNCS.get(self.operator)
        return func(value, self.threshold) if func else False

    def _read_cell_value(self):
        """
        Read the current numeric value of the watched cell from spreadsheet_raw.

        Uses the shared ``read_cell_value`` helper to locate the cell, then
        converts the result to float.  Returns None if the cell is absent or
        non-numeric.

        Note: For formula cells (=PIVOT(…)), the stored value in spreadsheet_raw
        is whatever was last computed client-side and saved.
        """
        raw = self.spreadsheet_id.sudo().spreadsheet_raw or {}
        value = read_cell_value(raw, self.cell_ref.strip(), self.sheet_name or None)
        if value is None:
            return None
        try:
            return float(str(value).replace(",", "."))
        except (ValueError, TypeError):
            return None

    def _fire_notification(self, value):
        """Post a Chatter alert message and email subscribers."""
        op_label = dict(_OPERATORS).get(self.operator, self.operator)
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        body = self.env["ir.qweb"]._render(
            "spreadsheet_oca.spreadsheet_alert_notification_template",
            {
                "alert": self,
                "value_str": f"{value:.4g}",
                "op_label": op_label,
                "threshold_str": f"{self.threshold:.4g}",
                "base_url": base_url,
            },
        )

        self.spreadsheet_id.sudo().message_post(
            body=body,
            subject=_("KPI Alert: %(name)s", name=self.name),
            partner_ids=self.notify_partner_ids.ids,
            subtype_xmlid=(
                "mail.mt_comment" if self.notify_partner_ids else "mail.mt_note"
            ),
        )

    def action_evaluate_now(self):
        """Manually trigger evaluation of this alert."""
        self.ensure_one()
        self._evaluate()

    def action_reset_state(self):
        """Reset last_state so an edge alert can trigger again."""
        self.write({"last_state": False})
