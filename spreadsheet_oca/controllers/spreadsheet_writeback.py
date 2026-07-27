# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Controller for cell writeback: edit list cells to update Odoo records.

The JS list cell-edit handler POSTs here with:
  spreadsheet_id  — int
  model           — str  (e.g. "sale.order")
  record_id       — int
  field_name      — str  (e.g. "name")
  new_value       — any  (JSON-decoded by Odoo's JSON-RPC dispatcher)

Returns a JSON-serialisable dict:
  {'success': True, 'old_value': str, 'new_value': str, 'log_id': int}
  or
  {'error': '<message>'}

All exceptions are caught so a writeback failure never results in a
500 error reaching the browser.
"""

import logging

from odoo import _
from odoo.exceptions import AccessError
from odoo.http import Controller, request, route

from ..models.spreadsheet_writeback import WRITEBACK_FIELD_TYPES

_logger = logging.getLogger(__name__)


class SpreadsheetWriteback(Controller):
    @route(
        "/spreadsheet/writeback",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def writeback(self, spreadsheet_id, model, record_id, field_name, new_value):
        """
        Write a single field value to an Odoo record on behalf of the
        spreadsheet's List cell-edit handler.

        Security checks (in order):
          1. spreadsheet.writeback_enabled must be True.
          2. Current user must have read access on the spreadsheet record.
          3. model must be a registered model in this environment.
          4. The target record must exist.
          5. Current user must have write access on the target record.

        The old value is captured before the write and stored in the audit
        log.  For relational fields str() is used which may not be
        directly re-writable; see the model docstring for details.
        """
        log_vals_base = {
            "spreadsheet_id": spreadsheet_id,
            "res_model": model,
            "record_id": record_id,
            "field_name": field_name,
            "new_value": str(new_value),
        }

        try:
            # 1. Load spreadsheet and check writeback_enabled
            spreadsheet = request.env["spreadsheet.spreadsheet"].browse(spreadsheet_id)
            if not spreadsheet.exists():
                return {"error": "Spreadsheet not found."}

            if not spreadsheet.writeback_enabled:
                return {"error": "Writeback not enabled for this spreadsheet."}

            # 2. Check spreadsheet read access
            try:
                spreadsheet.check_access("read")
            except AccessError:
                return {"error": "Access denied to spreadsheet."}

            # 3. Validate model
            if model not in request.env:
                return {"error": f"Model {model!r} is not available."}

            # 4. Load and check record existence
            record = request.env[model].browse(record_id)
            if not record.exists():
                return {"error": f"Record {model}({record_id}) not found."}

            # 5. Check write access on the target record
            try:
                record.check_access("write")
            except AccessError:
                _logger.warning(
                    "Writeback: user %d denied write on %s(%d)",
                    request.env.uid,
                    model,
                    record_id,
                )
                return {"error": "Access denied: no write access on record."}

            # 6. Validate field_name exists and is writable
            model_fields = request.env[model]._fields
            if field_name not in model_fields:
                return {
                    "error": _(
                        "Field %(field)s does not exist on model %(model)s.",
                        field=field_name,
                        model=model,
                    )
                }
            field_obj = model_fields[field_name]
            if field_obj.type not in WRITEBACK_FIELD_TYPES:
                return {
                    "error": _(
                        "Field %(field)s on %(model)s is a %(type)s field."
                        " Only simple value fields can be written back, because"
                        " the previous value is stored as text so it can be"
                        " rolled back.",
                        field=field_name,
                        model=model,
                        type=field_obj.type,
                    )
                }
            if field_obj.readonly or field_obj.compute:
                return {
                    "error": _(
                        "Field %(field)s on %(model)s is computed or readonly"
                        " and cannot be written to.",
                        field=field_name,
                        model=model,
                    )
                }

            # Capture old value before writing
            old_value = record[field_name]
            old_value_str = str(old_value)

            # Perform the write
            record.write({field_name: new_value})

            # Create audit log (sudo so the log can always be written
            # regardless of the user's access on spreadsheet.writeback.log)
            log = (
                request.env["spreadsheet.writeback.log"]
                .sudo()
                .create(
                    dict(
                        log_vals_base,
                        old_value=old_value_str,
                        status="ok",
                    )
                )
            )

            # Post a brief chatter note on the spreadsheet
            spreadsheet.sudo().message_post(
                body=_(
                    "Writeback: field <b>%(field)s</b> on "
                    "<b>%(model)s</b> #%(record_id)d changed "
                    "from <b>%(old)s</b> to <b>%(new)s</b>.",
                    field=field_name,
                    model=model,
                    record_id=record_id,
                    old=old_value_str,
                    new=str(new_value),
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
            _logger.exception(
                "Writeback error: spreadsheet=%d model=%s record=%d field=%s",
                spreadsheet_id,
                model,
                record_id,
                field_name,
            )
            # Attempt to write an error log (best effort — use sudo and
            # ignore any secondary failure so the route always returns JSON)
            try:
                request.env["spreadsheet.writeback.log"].sudo().create(
                    dict(
                        log_vals_base,
                        status="error",
                        error_message=str(exc)[:255],
                    )
                )
            except Exception:
                _logger.exception("Failed to create writeback error log")

            return {"error": str(exc)}
