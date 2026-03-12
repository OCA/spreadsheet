# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import zipfile
from io import BytesIO

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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

    refresh_schedule_count = fields.Integer(
        compute="_compute_refresh_schedule_count", string="Refresh Schedules"
    )

    def _compute_refresh_schedule_count(self):
        self._compute_related_count(
            "spreadsheet.refresh.schedule", "refresh_schedule_count"
        )

    alert_count = fields.Integer(compute="_compute_alert_count", string="KPI Alerts")

    def _compute_alert_count(self):
        self._compute_related_count("spreadsheet.alert", "alert_count")

    subscriber_count = fields.Integer(
        compute="_compute_subscriber_count", string="Subscribers"
    )

    def _compute_subscriber_count(self):
        self._compute_related_count("spreadsheet.subscription", "subscriber_count")

    def action_open_alerts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("KPI Alerts"),
            "res_model": "spreadsheet.alert",
            "view_mode": "list,form",
            "domain": [("spreadsheet_id", "=", self.id)],
            "context": {"default_spreadsheet_id": self.id},
        }

    def action_open_refresh_schedules(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Refresh Schedules"),
            "res_model": "spreadsheet.refresh.schedule",
            "view_mode": "list,form",
            "domain": [("spreadsheet_id", "=", self.id)],
            "context": {"default_spreadsheet_id": self.id},
        }

    def action_open_subscriptions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Subscribers"),
            "res_model": "spreadsheet.subscription",
            "view_mode": "list,form",
            "domain": [("spreadsheet_id", "=", self.id)],
            "context": {"default_spreadsheet_id": self.id},
        }

    scenario_count = fields.Integer(
        compute="_compute_scenario_count", string="What-If Scenarios"
    )

    def _compute_scenario_count(self):
        self._compute_related_count("spreadsheet.scenario", "scenario_count")

    def action_open_scenarios(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("What-If Scenarios"),
            "res_model": "spreadsheet.scenario",
            "view_mode": "list,form",
            "domain": [("spreadsheet_id", "=", self.id)],
            "context": {"default_spreadsheet_id": self.id},
        }

    input_param_count = fields.Integer(
        compute="_compute_input_param_count", string="Input Parameters"
    )

    def _compute_input_param_count(self):
        self._compute_related_count("spreadsheet.input_param", "input_param_count")

    def action_open_input_params(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Input Parameters"),
            "res_model": "spreadsheet.input_param",
            "view_mode": "list,form",
            "domain": [("spreadsheet_id", "=", self.id)],
            "context": {
                "default_spreadsheet_id": self.id,
                "search_default_active": 1,
            },
        }

    @api.depends("name")
    def _compute_filename(self):
        for record in self:
            record.filename = f"{record.name or _('Unnamed')}.json"

    # ── Writeback ─────────────────────────────────────────────────────────────
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

        record.write({log.field_name: log.old_value})
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

    # ── XLSX Export ───────────────────────────────────────────────────────────
    def action_export_xlsx(self):
        """Export this spreadsheet as .xlsx and return a download action."""
        from .spreadsheet_xlsx_export import SpreadsheetXlsxExporter

        self.ensure_one()
        exporter = SpreadsheetXlsxExporter(self.env, self)
        xlsx_bytes = exporter.render()

        filename = f"{self.name or 'spreadsheet'}.xlsx"
        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(xlsx_bytes),
                "mimetype": (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }

    @api.model
    def get_xlsx_bytes(self, spreadsheet_id):
        """Return raw .xlsx bytes (base64) for a spreadsheet."""
        from .spreadsheet_xlsx_export import SpreadsheetXlsxExporter

        spreadsheet = self.browse(spreadsheet_id)
        spreadsheet.check_access("read")
        exporter = SpreadsheetXlsxExporter(self.env, spreadsheet)
        return base64.b64encode(exporter.render()).decode()

    # ── Pivot Data ────────────────────────────────────────────────────────────
    @api.model
    def get_pivot_data(self, model_name, domain, context, row_dims, col_dims, measures):
        """Return pivot table data computed server-side (JSON-RPC entry point)."""
        from .pivot_data import _get_pivot_data

        return _get_pivot_data(
            self.env, model_name, domain, context, row_dims, col_dims, measures
        )

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
