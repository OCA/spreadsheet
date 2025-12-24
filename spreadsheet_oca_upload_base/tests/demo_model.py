from odoo import models


class DemoSpreadsheetUploadModel(models.Model):
    _name = "demo.spreadsheet.upload"
    _inherit = "spreadsheet.upload.mixin"
    _description = "Demo Model for Spreadsheet Upload Mixin"
