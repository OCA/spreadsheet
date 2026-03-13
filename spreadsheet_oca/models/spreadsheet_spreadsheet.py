# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import zipfile
from io import BytesIO

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .spreadsheet_writeback import coerce_old_value


class SpreadsheetSpreadsheet(models.Model):
    _name = "spreadsheet.spreadsheet"
    _inherit = ["spreadsheet.abstract", "mail.thread", "mail.activity.mixin"]
    _description = "Spreadsheet"

    filename = fields.Char(compute="_compute_filename")
    badge_image = fields.Image("Badge Background", max_width=1024, max_height=1024)
    owner_id = fields.Many2one(
        "res.users", required=True, default=lambda r: r.env.user.id
    )
    contributor_ids = fields.Many2many(
        "res.users",
        relation="spreadsheet_contributor",
        column1="spreadsheet_id",
        column2="user_id",
        string="Contributors",
    )
    contributor_group_ids = fields.Many2many(
        "res.groups",
        relation="spreadsheet_group_contributor",
        column1="spreadsheet_id",
        column2="group_id",
        string="Contributors Groups",
    )
    reader_ids = fields.Many2many(
        "res.users",
        relation="spreadsheet_reader",
        column1="spreadsheet_id",
        column2="user_id",
        string="Readers",
    )
    reader_group_ids = fields.Many2many(
        "res.groups",
        relation="spreadsheet_group_reader",
        column1="spreadsheet_id",
        column2="group_id",
        string="Readers Groups",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        help="If set, the spreadsheet will be available only"
        " if this company is in the current companies.",
    )

    spreadsheet_tag_ids = fields.Many2many(
        string="Tags", comodel_name="spreadsheet.spreadsheet.tag"
    )

    # ── DRY helper for read_group-based count fields ─────────────────────────

    def _compute_related_count(self, comodel, field_name, extra_domain=None):
        """Compute a count field by grouping *comodel* on ``spreadsheet_id``.

        By default the domain filters on ``active=True``; pass *extra_domain*
        to override (e.g. ``[("status", "!=", "error")]`` for writeback logs).
        """
        domain = [("spreadsheet_id", "in", self.ids)]
        if extra_domain is not None:
            domain += extra_domain
        else:
            domain.append(("active", "=", True))
        counts = self.env[comodel].read_group(
            domain, ["spreadsheet_id"], ["spreadsheet_id"]
        )
        count_map = {c["spreadsheet_id"][0]: c["spreadsheet_id_count"] for c in counts}
        for rec in self:
            rec[field_name] = count_map.get(rec.id, 0)

    @api.depends("name")
    def _compute_filename(self):
        for record in self:
            record.filename = f"{record.name or _('Unnamed')}.json"

    # ── Writeback ──────────────────────────────────────────────────────────
    writeback_enabled = fields.Boolean(
        default=False,
        tracking=True,
        help=(
            "Allow users to write Odoo record values directly from this "
            "spreadsheet's List views.  Each change is logged and reversible."
        ),
    )
    writeback_log_count = fields.Integer(
        compute="_compute_writeback_log_count",
    )

    def _compute_writeback_log_count(self):
        self._compute_related_count(
            "spreadsheet.writeback.log",
            "writeback_log_count",
            extra_domain=[("status", "!=", "error")],
        )

    def action_open_writeback_log(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Writeback Log"),
            "res_model": "spreadsheet.writeback.log",
            "view_mode": "list,form",
            "domain": [("spreadsheet_id", "=", self.id)],
            "context": {"default_spreadsheet_id": self.id},
        }

    @api.model
    def action_rollback_writeback(self, log_id):
        log = self.env["spreadsheet.writeback.log"].sudo().browse(log_id)
        if not log.exists():
            raise UserError(
                _("Writeback log entry %(log_id)d not found.", log_id=log_id)
            )

        if log.old_value is False or log.old_value is None:
            raise UserError(
                _(
                    "Cannot roll back log %(log_id)d: previous value is unknown.",
                    log_id=log_id,
                )
            )

        if log.res_model not in self.env:
            raise UserError(
                _(
                    "Cannot roll back log %(log_id)d:"
                    " model %(model)r is not available.",
                    log_id=log_id,
                    model=log.res_model,
                )
            )

        # Access check: ensure the calling user has write permission on the
        # target model/record before we escalate to sudo().
        self.env[log.res_model].check_access("write")
        record = self.env[log.res_model].browse(log.record_id)
        if not record.exists():
            raise UserError(
                _(
                    "Cannot roll back log %(log_id)d: record "
                    "%(model)s(%(record_id)d) no longer exists.",
                    log_id=log_id,
                    model=log.res_model,
                    record_id=log.record_id,
                )
            )
        record.check_access("write")

        field = record._fields.get(log.field_name)
        if field is None:
            raise UserError(
                _(
                    "Cannot roll back log %(log_id)d: field %(field)s no longer"
                    " exists on %(model)s.",
                    log_id=log_id,
                    field=log.field_name,
                    model=log.res_model,
                )
            )
        record.write({log.field_name: coerce_old_value(field, log.old_value)})
        log.write({"status": "rolled_back"})

        spreadsheet = log.spreadsheet_id.sudo()
        spreadsheet.message_post(
            body=_(
                "Writeback rolled back: field <b>%(field)s</b> on "
                "<b>%(model)s</b> #%(record_id)d restored to "
                "<b>%(old_value)s</b> (was <b>%(new_value)s</b>).",
                field=log.field_name,
                model=log.res_model,
                record_id=log.record_id,
                old_value=log.old_value,
                new_value=log.new_value,
            ),
            subtype_xmlid="mail.mt_note",
        )

        return True

    def create_document_from_attachment(self, attachment_ids):
        attachments = self.env["ir.attachment"].browse(attachment_ids)
        spreadsheets = self.env["spreadsheet.spreadsheet"]
        for attachment in attachments:
            extracted = {}
            with zipfile.ZipFile(
                BytesIO(base64.b64decode(attachment.datas)), "r"
            ) as xlsx:
                # List and filter for XML and REL files
                xml_files = [
                    f
                    for f in xlsx.namelist()
                    if f.endswith(".xml") or f.endswith(".rels")
                ]
                # Extract each file
                for xml_file in xml_files:
                    # Read the XML file into memory
                    with xlsx.open(xml_file) as file:
                        extracted[xml_file] = file.read().decode("UTF8")
                spreadsheets |= self.create(
                    {
                        "spreadsheet_raw": extracted,
                        "name": attachment.name,
                    }
                )
        attachments.unlink()
        if len(spreadsheets) == 1:
            return spreadsheets.get_formview_action()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "spreadsheet_oca.spreadsheet_spreadsheet_act_window"
        )
        action["domain"] = [("id", "in", spreadsheets.ids)]
        return action
