# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Named input parameters.

Users mark specific cells as named "input parameters."  A parameter stores
the cell's current value so that:

  1. Server-side domain substitution can reference it during scheduled refresh
     (e.g. ``[("date", ">=", "%(start_date)s")]``).
  2. A future JS side-panel can re-query pivot data sources in real time when
     an input cell changes (the JSON endpoint is already wired up).

This is the Python backend layer only.  The o-spreadsheet JS plugin work
required for live client-side re-query is a planned follow-on.
"""

import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .cell_ref import parse_cell_key, read_cell_value

_logger = logging.getLogger(__name__)

# Valid parameter names: start with a lowercase letter, then lowercase letters,
# digits, or underscores.  Mirrors Python %(name)s identifier conventions.
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class SpreadsheetInputParam(models.Model):
    _name = "spreadsheet.input_param"
    _description = "Spreadsheet Input Parameter"
    _inherit = ["mail.thread"]
    _order = "spreadsheet_id, name"

    name = fields.Char(
        required=True,
        tracking=True,
        help=(
            "Identifier used in domain templates as %(name)s.\n"
            "Must start with a lowercase letter and contain only lowercase letters, "
            "digits, and underscores."
        ),
    )
    spreadsheet_id = fields.Many2one(
        "spreadsheet.spreadsheet",
        required=True,
        ondelete="cascade",
        index=True,
    )
    cell_ref = fields.Char(
        string="Cell Reference",
        required=True,
        tracking=True,
        help=(
            "Cell to read the parameter value from.\n"
            "Use a bare reference (e.g. B3) or include the sheet name "
            "(e.g. Sheet1!B3)."
        ),
    )
    description = fields.Char(
        help="Optional human note explaining what this parameter controls.",
    )
    active = fields.Boolean(default=True, tracking=True)

    # ── Synced value ──────────────────────────────────────────────────────────
    current_value = fields.Char(
        readonly=True,
        copy=False,
        help="Last value read from the spreadsheet cell.",
    )
    last_synced = fields.Datetime(
        readonly=True,
        copy=False,
    )

    # ── Unique name per spreadsheet ───────────────────────────────────────────
    _sql_constraints = [
        (
            "unique_name_per_spreadsheet",
            "UNIQUE(spreadsheet_id, name)",
            "A parameter with this name already exists for this spreadsheet.",
        ),
    ]

    # ── Constraints ───────────────────────────────────────────────────────────

    @api.constrains("cell_ref")
    def _check_cell_ref(self):
        for rec in self:
            if not rec.cell_ref:
                continue
            _sheet, col, row = parse_cell_key(rec.cell_ref.strip())
            if col is None:
                raise ValidationError(
                    _("Cell reference %(ref)r is not valid. Use 'B3' or 'Sheet1!B3'.")
                    % {"ref": rec.cell_ref}
                )

    @api.constrains("name")
    def _check_name(self):
        for rec in self:
            if rec.name and not _NAME_RE.match(rec.name):
                raise ValidationError(
                    _(
                        "Parameter name %(name)r is not valid. "
                        "It must start with a lowercase letter and contain only "
                        "lowercase letters, digits, and underscores."
                    )
                    % {"name": rec.name}
                )

    # ── Sync logic ────────────────────────────────────────────────────────────

    def _sync_from_spreadsheet(self):
        """Read this parameter's cell from spreadsheet_raw and store the value."""
        self.ensure_one()
        raw = self.spreadsheet_id.sudo().spreadsheet_raw or {}
        value = read_cell_value(raw, self.cell_ref.strip())
        now = fields.Datetime.now()
        if value is not None:
            self.write({"current_value": str(value), "last_synced": now})
        else:
            self.write({"last_synced": now})

    def action_sync_now(self):
        """Manually trigger a sync for this parameter."""
        self.ensure_one()
        self._sync_from_spreadsheet()

    @api.model
    def _sync_all_for_spreadsheet(self, spreadsheet_id):
        """Sync all active input parameters for the given spreadsheet record ID."""
        params = self.search(
            [
                ("spreadsheet_id", "=", spreadsheet_id),
                ("active", "=", True),
            ]
        )
        for param in params:
            try:
                param._sync_from_spreadsheet()
            except Exception:
                _logger.exception(
                    "Failed to sync input param %s (%s) for spreadsheet %s",
                    param.id,
                    param.name,
                    spreadsheet_id,
                )
