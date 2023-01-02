# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import fields, models
from odoo.exceptions import AccessError


class SpreadsheetAbstract(models.AbstractModel):
    _name = "spreadsheet.abstract"
    _description = "Spreadsheet abstract for inheritance"

    name = fields.Char()
    raw = fields.Binary()

    def get_spreadsheet_data(self):
        self.ensure_one()
        mode = "normal"
        try:
            self.check_access_rights("write")
            self.check_access_rule("write")
        except AccessError:
            mode = "readonly"
        return {
            "name": self.name,
            "raw": self.raw,
            "mode": mode,
        }

    def open_spreadsheet(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "action_spreadsheet_oca",
            "params": {"spreadsheet_id": self.id, "model": self._name},
        }

    def send_spreadsheet_message(self, message):
        self.ensure_one()
        channel = "spreadsheet_oca;%s;%s" % (self._name, self.id)
        message.update({"res_model": self._name, "res_id": self.id})
        self.env["bus.bus"]._sendone(channel, "spreadsheet_oca", message)
        return True
