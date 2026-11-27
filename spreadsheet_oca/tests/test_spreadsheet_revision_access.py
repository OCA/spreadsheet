# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged

REVISION = "spreadsheet.oca.revision"


@tagged("post_install", "-at_install")
class TestSpreadsheetRevisionAccess(TransactionCase):
    """Revisions are only reachable through the spreadsheet they belong to:
    reading one requires read access to the spreadsheet, creating, changing
    or deleting one requires write access to it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.internal = new_test_user(
            cls.env, login="rev_internal", groups="base.group_user"
        )
        cls.owner = new_test_user(
            cls.env,
            login="rev_owner",
            groups="base.group_user,spreadsheet_oca.group_user",
        )
        cls.outsider = new_test_user(
            cls.env,
            login="rev_outsider",
            groups="base.group_user,spreadsheet_oca.group_user",
        )
        cls.reader = new_test_user(
            cls.env,
            login="rev_reader",
            groups="base.group_user,spreadsheet_oca.group_user",
        )
        cls.sheet = (
            cls.env["spreadsheet.spreadsheet"]
            .with_user(cls.owner)
            .create({"name": "Private sheet", "reader_ids": [(4, cls.reader.id)]})
        )
        cls.other_sheet = (
            cls.env["spreadsheet.spreadsheet"]
            .with_user(cls.outsider)
            .create({"name": "Outsider sheet"})
        )
        cls.revision = cls.env[REVISION].create(cls._revision_vals(cls.sheet, "a"))

    @classmethod
    def _revision_vals(cls, sheet, server_revision_id):
        return {
            "model": sheet._name,
            "res_id": sheet.id,
            "type": "REMOTE_REVISION",
            "server_revision_id": server_revision_id,
            "next_revision_id": server_revision_id + "+",
            "commands": json.dumps({"type": "REMOTE_REVISION", "commands": []}),
        }

    def _message(self, server_revision_id):
        return {
            "type": "REMOTE_REVISION",
            "serverRevisionId": server_revision_id,
            "nextRevisionId": server_revision_id + "+",
            "clientId": "client",
            "commands": [],
        }

    def _assert_no_access(self, user):
        Revision = self.env[REVISION].with_user(user)
        self.assertFalse(Revision.search([("id", "=", self.revision.id)]))
        self.assertNotIn(
            self.revision.id, [r["id"] for r in Revision.search_read([], ["id"])]
        )
        with self.assertRaises(AccessError):
            self.revision.with_user(user).read(["commands"])
        with self.assertRaises(AccessError):
            Revision.create(self._revision_vals(self.sheet, "b"))
        with self.assertRaises(AccessError):
            self.revision.with_user(user).write({"commands": "{}"})
        with self.assertRaises(AccessError):
            self.revision.with_user(user).unlink()
        self.assertTrue(self.revision.exists())

    def test_internal_user_without_spreadsheet_access(self):
        self._assert_no_access(self.internal)

    def test_spreadsheet_user_without_access_to_the_sheet(self):
        self._assert_no_access(self.outsider)

    def test_reader_reads_but_cannot_change(self):
        sheet = self.sheet.with_user(self.reader)
        data = sheet.get_spreadsheet_data()
        self.assertEqual(data["mode"], "readonly")
        self.assertEqual(len(data["revisions"]), 1)
        self.assertEqual(
            self.revision.with_user(self.reader).commands,
            json.dumps({"type": "REMOTE_REVISION", "commands": []}),
        )
        Revision = self.env[REVISION].with_user(self.reader)
        with self.assertRaises(AccessError):
            Revision.create(self._revision_vals(self.sheet, "b"))
        with self.assertRaises(AccessError):
            self.revision.with_user(self.reader).write({"commands": "{}"})
        with self.assertRaises(AccessError):
            self.revision.with_user(self.reader).unlink()
        with self.assertRaises(AccessError):
            sheet.send_spreadsheet_message(self._message("b"))

    def test_owner_keeps_editing(self):
        sheet = self.sheet.with_user(self.owner)
        self.assertTrue(sheet.send_spreadsheet_message(self._message("b")))
        # res_id is an Integer, so a new revision does not refresh the cached
        # one2many: a real client reads it in a later request.
        self.env.invalidate_all()
        data = sheet.get_spreadsheet_data()
        self.assertEqual(data["mode"], "normal")
        self.assertEqual(len(data["revisions"]), 2)
        revision = (
            self.env[REVISION]
            .with_user(self.owner)
            .create(self._revision_vals(self.sheet, "c"))
        )
        revision.write({"commands": "{}"})
        revision.unlink()
        # Saving the document drops its revisions, as the owner.
        sheet.write({"spreadsheet_raw": {"sheets": []}})
        self.assertFalse(self.sheet.spreadsheet_revision_ids)

    def test_archived_sheet_keeps_its_revisions_visible(self):
        self.sheet.with_user(self.owner).active = False
        revisions = (
            self.env[REVISION]
            .with_user(self.owner)
            .search([("res_id", "=", self.sheet.id), ("model", "=", self.sheet._name)])
        )
        self.assertEqual(revisions, self.revision)

    def test_cannot_move_a_revision_to_a_sheet_without_write_access(self):
        revision = (
            self.env[REVISION]
            .with_user(self.owner)
            .create(self._revision_vals(self.sheet, "c"))
        )
        with self.assertRaises(AccessError):
            revision.write({"res_id": self.other_sheet.id})

    def test_revision_must_belong_to_a_spreadsheet(self):
        """A revision cannot be attached to a record that is not a
        spreadsheet, even one the user can write."""
        user = new_test_user(
            self.env,
            login="rev_partner_manager",
            groups="base.group_user,base.group_partner_manager,"
            "spreadsheet_oca.group_user",
        )
        partner = self.env["res.partner"].with_user(user).create({"name": "P"})
        partner.write({"name": "Q"})
        with self.assertRaises(AccessError):
            self.env[REVISION].with_user(user).create(
                dict(
                    self._revision_vals(self.sheet, "z"),
                    model="res.partner",
                    res_id=partner.id,
                )
            )

    def test_superuser_is_not_restricted(self):
        self.assertIn(self.revision, self.env[REVISION].search([]))

    def test_import_wizard_is_private_to_its_creator(self):
        wizard = (
            self.env["spreadsheet.spreadsheet.import"]
            .with_user(self.owner)
            .create({"name": "Mine", "datasource_name": "Mine"})
        )
        Wizard = self.env["spreadsheet.spreadsheet.import"].with_user(self.outsider)
        self.assertFalse(Wizard.search([("id", "=", wizard.id)]))
        with self.assertRaises(AccessError):
            wizard.with_user(self.outsider).read(["name"])
        self.assertEqual(wizard.with_user(self.owner).name, "Mine")
