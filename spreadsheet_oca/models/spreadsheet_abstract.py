# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
from typing import Any

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

CollaborationMessage = dict[str, Any]


class SpreadsheetAbstract(models.AbstractModel):
    _name = "spreadsheet.abstract"
    _description = "Spreadsheet abstract for inheritance"
    _inherit = ["bus.listener.mixin"]

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    spreadsheet_binary_data = fields.Binary(
        string="Spreadsheet file",
        default=lambda self: self._empty_spreadsheet_data_base64(),
    )
    spreadsheet_raw = fields.Serialized(
        inverse="_inverse_spreadsheet_raw", compute="_compute_spreadsheet_raw"
    )
    spreadsheet_revision_ids = fields.One2many(
        "spreadsheet.oca.revision",
        inverse_name="res_id",
        domain=lambda r: [("model", "=", r._name)],
    )

    @api.depends("spreadsheet_binary_data")
    def _compute_spreadsheet_raw(self):
        for dashboard in self:
            if dashboard.spreadsheet_binary_data:
                dashboard.spreadsheet_raw = json.loads(
                    base64.decodebytes(dashboard.spreadsheet_binary_data).decode(
                        "UTF-8"
                    )
                )
            else:
                dashboard.spreadsheet_raw = {}

    def _inverse_spreadsheet_raw(self):
        for record in self:
            record.spreadsheet_binary_data = base64.encodebytes(
                json.dumps(record.spreadsheet_raw).encode("UTF-8")
            )

    def _empty_spreadsheet_data_base64(self):
        """Create an empty spreadsheet workbook.
        Encoded as base64
        """
        data = json.dumps(self._empty_spreadsheet_data())
        return base64.b64encode(data.encode())

    def _empty_spreadsheet_data(self):
        """Create an empty spreadsheet workbook.
        The sheet name should be the same for all users to allow consistent references
        in formulas. It is translated for the user creating the spreadsheet.
        """
        lang = self.env["res.lang"]._lang_get(self.env.user.lang)
        locale = lang._odoo_lang_to_spreadsheet_locale()
        return {
            "version": 1,
            "sheets": [
                {
                    "id": "sheet1",
                    "name": _("Sheet1"),
                }
            ],
            "settings": {
                "locale": locale,
            },
            "revisionId": "START_REVISION",
        }

    def get_spreadsheet_data(self):
        self.ensure_one()
        mode = "normal"
        try:
            self.check_access("write")
        except AccessError:
            mode = "readonly"
        spreadsheet_raw, revisions = self._get_spreadsheet_revisions_payload()
        return {
            "name": self.name,
            "spreadsheet_raw": spreadsheet_raw,
            "revisions": revisions,
            "mode": mode,
            "default_currency": self.env[
                "res.currency"
            ].get_company_currency_for_spreadsheet(),
            "user_locale": self.env["res.lang"]._get_user_spreadsheet_locale(),
        }

    def _spreadsheet_revision_domain(self):
        self.ensure_one()
        return [("model", "=", self._name), ("res_id", "=", self.id)]

    def _get_last_spreadsheet_snapshot_revision(self):
        return self.env["spreadsheet.oca.revision"].search(
            self._spreadsheet_revision_domain() + [("type", "=", "SNAPSHOT")],
            order="id desc",
            limit=1,
        )

    def _get_spreadsheet_revisions_payload(self):
        """Build workbook + pending revisions without loading compacted history.

        ``get_spreadsheet_data`` used to browse every ``spreadsheet.oca.revision``
        and ``json.loads`` of ``commands``. Paste of large ranges creates one
        UPDATE_CELL per cell; SNAPSHOT used to store the whole workbook as
        another revision. That combination MemoryErrors on open.

        After a SNAPSHOT, only later revisions are returned. Legacy SNAPSHOT
        rows that still embed ``data`` are used as the workbook base.
        """
        last_snapshot = self._get_last_spreadsheet_snapshot_revision()
        spreadsheet_raw = self.spreadsheet_raw
        if last_snapshot and last_snapshot.commands:
            snapshot_commands = json.loads(last_snapshot.commands)
            if snapshot_commands.get("data"):
                spreadsheet_raw = snapshot_commands["data"]
        domain = self._spreadsheet_revision_domain()
        if last_snapshot:
            domain = domain + [("id", ">", last_snapshot.id)]
        pending = self.env["spreadsheet.oca.revision"].search(domain, order="id")
        revisions = [
            dict(
                json.loads(revision.commands),
                nextRevisionId=revision.next_revision_id,
                serverRevisionId=revision.server_revision_id,
            )
            for revision in pending
        ]
        return spreadsheet_raw, revisions

    def open_spreadsheet(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "action_spreadsheet_oca",
            "params": {"spreadsheet_id": self.id, "model": self._name},
        }

    def send_spreadsheet_message(
        self, message: CollaborationMessage, access_token=None
    ):
        self.ensure_one()
        if message["type"] in ["REVISION_UNDONE", "REMOTE_REVISION", "REVISION_REDONE"]:
            self._check_access_spreadsheet("write")
            self.env["spreadsheet.oca.revision"].create(
                {
                    "model": self._name,
                    "res_id": self.id,
                    "type": message["type"],
                    "client_id": message.get("clientId"),
                    "next_revision_id": message["nextRevisionId"],
                    "server_revision_id": message["serverRevisionId"],
                    "commands": json.dumps(
                        self._build_spreadsheet_revision_commands_data(message)
                    ),
                }
            )
            self._bus_send(
                "notification", dict(message, id=self.id), subchannel="spreadsheet_oca"
            )
            return True
        elif message["type"] == "SNAPSHOT":
            self._check_access_spreadsheet("write")
            return self._snapshot_spreadsheet(message)
        elif message["type"] in ["CLIENT_JOINED", "CLIENT_LEFT", "CLIENT_MOVED"]:
            self._check_access_spreadsheet("read")
            self._bus_send(
                "notification", dict(message, id=self.id), subchannel="spreadsheet_oca"
            )
            return True
        return False

    def _check_access_spreadsheet(self, operation: str):
        try:
            self.check_access(operation)
        except AccessError as e:
            raise e
        return True

    def _snapshot_spreadsheet(self, message):
        """Persist snapshot as the new workbook base and drop prior revisions.

        Same idea as o-spreadsheet/Enterprise: SNAPSHOT is not stored as a
        giant revision. Collaborators receive SNAPSHOT_CREATED. o-spreadsheet
        already snapshots on leave when no other client is connected.
        """
        snapshot_data = message.get("data")
        if not snapshot_data:
            return False
        next_revision_id = message["nextRevisionId"]
        if snapshot_data.get("revisionId") != next_revision_id:
            raise ValueError("The snapshot revision id does not match the revision id")
        self.write({"spreadsheet_raw": snapshot_data})
        self._bus_send(
            "notification",
            {
                "type": "SNAPSHOT_CREATED",
                "serverRevisionId": message["serverRevisionId"],
                "nextRevisionId": next_revision_id,
                "id": self.id,
            },
            subchannel="spreadsheet_oca",
        )
        return True

    @api.model
    def _build_spreadsheet_revision_commands_data(self, message):
        """Prepare spreadsheet revision commands data from the message"""
        commands = dict(message)
        commands.pop("serverRevisionId", None)
        commands.pop("nextRevisionId", None)
        commands.pop("clientId", None)
        return commands

    def _unlink_spreadsheet_revisions(self):
        """Unlink collaboration history without prefetching ``commands``.

        Those Char values can be huge (one UPDATE_CELL per pasted cell). Loading
        them only to delete the rows would MemoryError the same way as open.
        """
        Revision = self.env["spreadsheet.oca.revision"].with_context(
            prefetch_fields=False
        )
        for record in self:
            Revision.search(
                [("model", "=", record._name), ("res_id", "=", record.id)]
            ).unlink()

    def write(self, vals):
        if "spreadsheet_raw" in vals:
            self._unlink_spreadsheet_revisions()
        return super().write(vals)
