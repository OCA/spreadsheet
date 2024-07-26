# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SpreadsheetOcaRevision(models.Model):
    _name = "spreadsheet.oca.revision"
    _description = "Spreadsheet Oca Revision"  # TODO

    model = fields.Char(required=True)
    res_id = fields.Integer(required=True, index=True)
    type = fields.Char()
    client_id = fields.Char()
    server_revision_id = fields.Char()
    next_revision_id = fields.Char()
    commands = fields.Char()
