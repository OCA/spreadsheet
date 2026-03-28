# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import zipfile
from io import BytesIO

from odoo import _, api, fields, models


class SpreadsheetSpreadsheet(models.Model):
    _name = "spreadsheet.spreadsheet"
    _inherit = "spreadsheet.abstract"
    _description = "Spreadsheet"

    filename = fields.Char(compute="_compute_filename")
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

    @api.depends("name")
    def _compute_filename(self):
        for record in self:
            record.filename = "%s.json" % (self.name or _("Unnamed"))

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
