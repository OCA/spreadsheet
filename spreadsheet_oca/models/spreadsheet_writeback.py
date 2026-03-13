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

old_value is stored as text, so writeback is restricted to the field
types whose value survives a str() round-trip — see WRITEBACK_FIELD_TYPES.
Relational and binary fields are rejected at the controller rather than
stored in a form that cannot be rolled back.

Rolling a value back goes through coerce_old_value(), which converts the
stored text back to the field's own type.  Booleans matter most here:
str(False) is "False", and writing that string straight back would set the
field to True, because a non-empty string is truthy.
"""

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

# Field types whose value survives being stored as text and written back.
# Relational and binary types are deliberately absent: str(recordset) yields
# e.g. "res.partner(7,)", which cannot be written back to the field.
WRITEBACK_FIELD_TYPES = {
    "char",
    "text",
    "integer",
    "float",
    "monetary",
    "boolean",
    "date",
    "datetime",
    "selection",
}


def coerce_old_value(field, stored):
    """Convert a stored old_value string back to *field*'s own type.

    Odoo coerces text to date, datetime, selection and the numeric types on
    write, but not to boolean — ``bool("False")`` is True — so booleans are
    converted explicitly.
    """
    if field.type == "boolean":
        return str(stored).strip().lower() in ("true", "1")
    if field.type == "integer":
        return int(float(stored))
    if field.type in ("float", "monetary"):
        return float(stored)
    return stored


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
