# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Cell writeback: edit list cells to update Odoo records.

Allows users to write Odoo record field values directly from a
spreadsheet's List view.  Each cell edit in the browser posts to
/spreadsheet/writeback (controllers/spreadsheet_writeback.py) which
calls the target model's write() and records an audit log entry here.

JavaScript integration (not yet implemented): the JS list cell-edit
handler will POST to /spreadsheet/writeback with the spreadsheet_id,
model, record_id, field_name and new_value.  The controller returns a
JSON dict with {success, old_value, new_value, log_id} or {error}.

Limitations of the old_value capture:
  - Field values are converted to str() before storage in the Char
    field.  For Many2one fields str() gives e.g. "product.product(42,)"
    which is not directly re-writable; rollback of many2one fields is
    therefore only possible for integer / char / float / selection fields
    where str→original type conversion is unambiguous.
  - The rollback helper (action_rollback_writeback) writes old_value as
    a raw string; callers that need type-safe rollback for relational
    fields should implement their own conversion before calling write().
"""

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SpreadsheetWritebackLog(models.Model):
    _name = "spreadsheet.writeback.log"
    _description = "Spreadsheet Writeback Audit Log"
    _order = "writeback_at desc"

    spreadsheet_id = fields.Many2one(
        "spreadsheet.spreadsheet",
        required=True,
        ondelete="cascade",
        index=True,
        string="Spreadsheet",
    )
    res_model = fields.Char(required=True, string="Model")
    record_id = fields.Integer(required=True)
    field_name = fields.Char(required=True, string="Field")
    old_value = fields.Char(string="Previous Value")
    new_value = fields.Char(required=True)
    user_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        readonly=True,
    )
    writeback_at = fields.Datetime(
        default=fields.Datetime.now,
        readonly=True,
        string="Written At",
    )
    status = fields.Selection(
        [
            ("ok", "Success"),
            ("error", "Error"),
            ("rolled_back", "Rolled Back"),
        ],
        default="ok",
    )
    error_message = fields.Char(string="Error")

    def action_rollback(self):
        """
        Roll back this log entry by restoring old_value to the target record.

        Called from the form view "Roll Back" button (type="object").
        Delegates to SpreadsheetSpreadsheet.action_rollback_writeback so the
        rollback logic lives in one place.
        """
        self.ensure_one()
        self.spreadsheet_id.action_rollback_writeback(self.id)
