from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SpreadsheetUploadMixin(models.AbstractModel):
    _name = "spreadsheet.upload.mixin"
    _description = "Mixin to upload XLSX and create linked spreadsheet"

    spreadsheet_id = fields.Many2one(
        comodel_name="spreadsheet.spreadsheet",
        string="Spreadsheet",
        help="Linked Spreadsheet",
        copy=False,
    )
    upload_file = fields.Binary(
        string="Upload XLSX", copy=False, help="XLSX file to upload"
    )
    file_name = fields.Char(copy=False, help="Name of the uploaded file")

    @api.constrains("file_name")
    def _check_xlsx_file_type(self):
        """New constraint to check uploaded file type is XLSX."""
        invalid_files = self.filtered(
            lambda spreadsheet: not spreadsheet.file_name.lower().endswith(".xlsx")
        )
        if invalid_files:
            raise ValidationError(_("Please upload a valid XLSX file."))

    def _get_attachment(self):
        """New method to search for the attachment of the uploaded file."""
        self.ensure_one()
        attachment = self.env["ir.attachment"].search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("res_field", "=", "upload_file"),
            ],
            limit=1,
        )
        if attachment:
            attachment.write(
                {
                    "name": self.file_name or "uploaded_file",
                }
            )
        return attachment

    def action_create_spreadsheet(self):
        """New method to create spredsheet from the upload file."""
        for record in self:
            attachment = record._get_attachment()
            if not attachment:
                continue
            spreadsheet = self.env[
                "spreadsheet.spreadsheet"
            ].create_document_from_attachment([attachment.id])
            record.spreadsheet_id = spreadsheet.get("res_id") if spreadsheet else False

    def action_open_spreadsheet(self):
        """New method to open linked spredsheet."""
        self.ensure_one()
        if not self.spreadsheet_id:
            return
        return self.spreadsheet_id.open_spreadsheet()
