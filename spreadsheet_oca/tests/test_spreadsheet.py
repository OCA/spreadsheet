# Copyright 2026 arielbarreiros96
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
import zipfile
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from odoo.exceptions import AccessDenied, AccessError
from odoo.tests.common import TransactionCase, new_test_user

WS_MODULE = "odoo.addons.bus.models.ir_websocket"


class TestSpreadsheet(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Spreadsheet = cls.env["spreadsheet.spreadsheet"]
        cls.spreadsheet = cls.Spreadsheet.create({"name": "Test Spreadsheet"})

    def _message(self, message_type, **extra):
        return dict(
            {
                "type": message_type,
                "clientId": "client-1",
                "nextRevisionId": "next-1",
                "serverRevisionId": "server-1",
            },
            **extra,
        )

    def test_new_spreadsheet_has_empty_workbook(self):
        raw = self.spreadsheet.spreadsheet_raw
        self.assertEqual(raw["version"], 1)
        self.assertEqual(raw["sheets"][0]["id"], "sheet1")
        self.assertIn("revisionId", raw)

    def test_spreadsheet_raw_roundtrip(self):
        data = {"version": 1, "sheets": [], "revisionId": "R1"}
        self.spreadsheet.spreadsheet_raw = data
        self.assertEqual(self.spreadsheet.spreadsheet_raw, data)
        decoded = json.loads(
            base64.decodebytes(self.spreadsheet.spreadsheet_binary_data).decode("UTF-8")
        )
        self.assertEqual(decoded, data)

    def test_open_spreadsheet_action(self):
        action = self.spreadsheet.open_spreadsheet()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "action_spreadsheet_oca")
        self.assertEqual(action["params"]["spreadsheet_id"], self.spreadsheet.id)
        self.assertEqual(action["params"]["model"], "spreadsheet.spreadsheet")

    def test_get_spreadsheet_data(self):
        data = self.spreadsheet.get_spreadsheet_data()
        self.assertEqual(data["name"], self.spreadsheet.name)
        self.assertEqual(data["mode"], "normal")
        self.assertEqual(data["revisions"], [])
        self.assertIn("default_currency", data)
        self.assertIn("user_locale", data)

    def test_send_revision_message_creates_revision(self):
        result = self.spreadsheet.send_spreadsheet_message(
            self._message("REMOTE_REVISION")
        )
        self.assertTrue(result)
        revision = self.spreadsheet.spreadsheet_revision_ids
        self.assertEqual(len(revision), 1)
        self.assertEqual(revision.next_revision_id, "next-1")
        self.assertEqual(revision.server_revision_id, "server-1")
        commands = json.loads(revision.commands)
        self.assertNotIn("serverRevisionId", commands)
        self.assertNotIn("nextRevisionId", commands)
        self.assertNotIn("clientId", commands)
        self.assertEqual(commands["type"], "REMOTE_REVISION")

    def test_send_snapshot_message_creates_revision(self):
        result = self.spreadsheet.send_spreadsheet_message(self._message("SNAPSHOT"))
        self.assertTrue(result)
        self.assertEqual(len(self.spreadsheet.spreadsheet_revision_ids), 1)

    def test_send_presence_message_creates_no_revision(self):
        result = self.spreadsheet.send_spreadsheet_message(
            self._message("CLIENT_MOVED")
        )
        self.assertTrue(result)
        self.assertFalse(self.spreadsheet.spreadsheet_revision_ids)

    def test_send_unknown_message_returns_false(self):
        self.assertFalse(
            self.spreadsheet.send_spreadsheet_message(self._message("SOMETHING"))
        )

    def test_send_revision_denied_without_write(self):
        user = new_test_user(
            self.env, login="ssheet_ro", groups="spreadsheet_oca.group_user"
        )
        self.spreadsheet.reader_ids = user
        with self.assertRaises(AccessError):
            self.spreadsheet.with_user(user).send_spreadsheet_message(
                self._message("REMOTE_REVISION")
            )

    def test_writing_raw_clears_revisions(self):
        self.spreadsheet.send_spreadsheet_message(self._message("SNAPSHOT"))
        self.assertTrue(self.spreadsheet.spreadsheet_revision_ids)
        self.spreadsheet.spreadsheet_raw = {
            "version": 1,
            "sheets": [],
            "revisionId": "X",
        }
        self.assertFalse(self.spreadsheet.spreadsheet_revision_ids)

    def test_get_spreadsheet_data_returns_stored_revisions(self):
        self.spreadsheet.send_spreadsheet_message(self._message("REMOTE_REVISION"))
        data = self.spreadsheet.get_spreadsheet_data()
        self.assertEqual(len(data["revisions"]), 1)
        self.assertEqual(data["revisions"][0]["nextRevisionId"], "next-1")
        self.assertEqual(data["revisions"][0]["serverRevisionId"], "server-1")

    def test_compute_filename(self):
        self.spreadsheet.name = "My Sheet"
        self.assertEqual(self.spreadsheet.filename, "My Sheet.json")

    def test_tag_default_color(self):
        tag = self.env["spreadsheet.spreadsheet.tag"].create({"name": "A Tag"})
        self.assertTrue(1 <= tag.color <= 11)

    def _xlsx_attachment(self, name="Book.xlsx"):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("xl/worksheets/sheet1.xml", "<worksheet/>")
            archive.writestr("xl/_rels/workbook.xml.rels", "<Relationships/>")
        return self.env["ir.attachment"].create(
            {"name": name, "datas": base64.b64encode(buffer.getvalue())}
        )

    def test_create_document_from_attachment_single(self):
        attachment = self._xlsx_attachment()
        action = self.Spreadsheet.create_document_from_attachment(attachment.ids)
        self.assertEqual(action["res_model"], "spreadsheet.spreadsheet")
        self.assertTrue(action.get("res_id"))
        self.assertFalse(attachment.exists())

    def test_create_document_from_attachment_multiple(self):
        attachments = self._xlsx_attachment("A.xlsx") | self._xlsx_attachment("B.xlsx")
        action = self.Spreadsheet.create_document_from_attachment(attachments.ids)
        self.assertEqual(action["res_model"], "spreadsheet.spreadsheet")
        self.assertEqual(action["domain"][0][0], "id")

    def test_has_parent_relation(self):
        IrModel = self.env["ir.model"]
        self.assertTrue(IrModel.has_parent_relation("res.partner"))
        self.assertFalse(IrModel.has_parent_relation("spreadsheet.spreadsheet"))
        self.assertFalse(IrModel.has_parent_relation("no.such.model"))

    def _build_channels(self, channels, user=None):
        websocket = self.env["ir.websocket"]
        if user is not None:
            websocket = websocket.with_user(user)
        fake_request = SimpleNamespace(session=SimpleNamespace(uid=websocket.env.uid))
        with (
            patch(WS_MODULE + ".request", fake_request),
            patch(WS_MODULE + ".wsrequest", fake_request),
        ):
            result = websocket._build_bus_channel_list(list(channels))
        # Keep only spreadsheet_oca access tuples: the base method also returns
        # recordset-bearing channels, and comparing those in membership checks
        # triggers recordset.__eq__ warnings that fail CI.
        return [
            channel
            for channel in result
            if isinstance(channel, tuple)
            and channel
            and isinstance(channel[-1], str)
            and channel[-1] == "spreadsheet_oca"
        ]

    def _access_tuple(self, res_id):
        return (
            self.env.registry.db_name,
            "spreadsheet.spreadsheet",
            res_id,
            "spreadsheet_oca",
        )

    def test_websocket_channel_grants_access(self):
        channel = f"spreadsheet_oca;spreadsheet.spreadsheet;{self.spreadsheet.id}"
        result = self._build_channels([channel])
        self.assertIn(self._access_tuple(self.spreadsheet.id), result)

    def test_websocket_ignores_unrelated_channels(self):
        self.assertEqual(self._build_channels(["some_channel"]), [])

    def test_websocket_skips_missing_document(self):
        channel = "spreadsheet_oca;spreadsheet.spreadsheet;999999999"
        result = self._build_channels([channel])
        self.assertNotIn(self._access_tuple(999999999), result)

    def test_websocket_skips_without_model_access(self):
        user = new_test_user(self.env, login="ssheet_noacc", groups="base.group_user")
        channel = f"spreadsheet_oca;spreadsheet.spreadsheet;{self.spreadsheet.id}"
        result = self._build_channels([channel], user=user)
        self.assertNotIn(self._access_tuple(self.spreadsheet.id), result)

    def test_websocket_denies_non_internal_user(self):
        portal = new_test_user(
            self.env, login="ssheet_portal", groups="base.group_portal"
        )
        channel = f"spreadsheet_oca;spreadsheet.spreadsheet;{self.spreadsheet.id}"
        with self.assertRaises(AccessDenied):
            self.env["ir.websocket"].with_user(portal)._build_bus_channel_list(
                [channel]
            )
