# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo import fields, models
from odoo.exceptions import AccessError


class SpreadsheetAbstract(models.AbstractModel):
    _name = "spreadsheet.abstract"
    _description = "Spreadsheet abstract for inheritance"

    name = fields.Char(required=True)
    spreadsheet_raw = fields.Serialized()
    spreadsheet_revision_ids = fields.One2many(
        "spreadsheet.oca.revision",
        inverse_name="res_id",
        domain=lambda r: [("model", "=", r._name)],
    )

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
            "spreadsheet_raw": self.spreadsheet_raw,
            "revisions": [
                {
                    "type": revision.type,
                    "clientId": revision.client_id,
                    "nextRevisionId": revision.next_revision_id,
                    "serverRevisionId": revision.server_revision_id,
                    "commands": json.loads(revision.commands),
                }
                for revision in self.spreadsheet_revision_ids
            ],
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
        if message["type"] in ["REVISION_UNDONE", "REMOTE_REVISION", "REVISION_REDONE"]:
            self.env["spreadsheet.oca.revision"].create(
                {
                    "model": self._name,
                    "res_id": self.id,
                    "type": message["type"],
                    "client_id": message["clientId"],
                    "next_revision_id": message["nextRevisionId"],
                    "server_revision_id": message["serverRevisionId"],
                    "commands": json.dumps(message["commands"]),
                }
            )
        self.env["bus.bus"]._sendone(channel, "spreadsheet_oca", message)
        return True

    def write(self, vals):
        if "spreadsheet_raw" in vals:
            self.spreadsheet_revision_ids.unlink()
        return super().write(vals)
