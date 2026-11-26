# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestDashboardAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.viewer = new_test_user(
            cls.env, login="dash_viewer", groups="base.group_user"
        )
        cls.manager = new_test_user(
            cls.env,
            login="dash_manager",
            groups="base.group_user,spreadsheet_dashboard.group_dashboard_manager,"
            "spreadsheet_oca.group_user",
        )
        cls.section = cls.env["spreadsheet.dashboard.group"].create({"name": "S"})
        cls.dashboard = cls.env["spreadsheet.dashboard"].create(
            {"name": "Dashboard", "dashboard_group_id": cls.section.id}
        )
        cls.restricted = cls.env["spreadsheet.dashboard"].create(
            {
                "name": "Restricted",
                "dashboard_group_id": cls.section.id,
                "group_ids": [(6, 0, cls.env.ref("base.group_system").ids)],
            }
        )

    def _message(self, server_revision_id):
        return {
            "type": "REMOTE_REVISION",
            "serverRevisionId": server_revision_id,
            "nextRevisionId": server_revision_id + "+",
            "clientId": "client",
            "commands": [],
        }

    def test_manager_edits_and_viewer_reads(self):
        self.assertTrue(
            self.dashboard.with_user(self.manager).send_spreadsheet_message(
                self._message("a")
            )
        )
        self.env.invalidate_all()
        data = self.dashboard.with_user(self.viewer).get_spreadsheet_data()
        self.assertEqual(data["mode"], "readonly")
        self.assertEqual(len(data["revisions"]), 1)
        revision = self.dashboard.spreadsheet_revision_ids
        with self.assertRaises(AccessError):
            revision.with_user(self.viewer).write({"commands": "{}"})
        with self.assertRaises(AccessError):
            revision.with_user(self.viewer).unlink()

    def test_viewer_cannot_read_revisions_of_a_hidden_dashboard(self):
        self.restricted.send_spreadsheet_message(self._message("a"))
        revision = self.restricted.spreadsheet_revision_ids
        self.assertTrue(revision)
        Revision = self.env["spreadsheet.oca.revision"].with_user(self.viewer)
        self.assertFalse(Revision.search([("id", "in", revision.ids)]))
        with self.assertRaises(AccessError):
            revision.with_user(self.viewer).read(["commands"])

    def test_to_dashboard_wizard_is_private_to_its_creator(self):
        sheet = (
            self.env["spreadsheet.spreadsheet"]
            .with_user(self.manager)
            .create({"name": "Sheet"})
        )
        wizard = (
            self.env["spreadsheet.to.dashboard"]
            .with_user(self.manager)
            .create({"spreadsheet_id": sheet.id, "dashboard_group_id": self.section.id})
        )
        Wizard = self.env["spreadsheet.to.dashboard"].with_user(self.viewer)
        self.assertFalse(Wizard.search([("id", "=", wizard.id)]))
        with self.assertRaises(AccessError):
            wizard.with_user(self.viewer).read(["name"])
        self.assertTrue(wizard.with_user(self.manager).name)
