# Copyright 2026 arielbarreiros96
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestImportWizard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env["spreadsheet.spreadsheet.import"]
        cls.mode_new = cls.env.ref("spreadsheet_oca.spreadsheet_import_mode_new")
        cls.mode_add = cls.env.ref("spreadsheet_oca.spreadsheet_import_mode_add")

    def test_default_mode_is_set(self):
        wizard = self.Wizard.create({"name": "X"})
        self.assertTrue(wizard.mode_id)

    def test_insert_pivot_new_creates_spreadsheet(self):
        wizard = self.Wizard.create(
            {
                "name": "New Sheet",
                "datasource_name": "My Source",
                "mode_id": self.mode_new.id,
                "import_data": {"foo": "bar"},
            }
        )
        action = wizard.insert_pivot()
        self.assertEqual(action["tag"], "action_spreadsheet_oca")
        spreadsheet = self.env["spreadsheet.spreadsheet"].browse(
            action["params"]["spreadsheet_id"]
        )
        self.assertEqual(spreadsheet.name, "New Sheet")
        self.assertEqual(action["params"]["import_data"]["name"], "My Source")
        self.assertEqual(action["params"]["import_data"]["new"], 1)

    def test_insert_pivot_new_dynamic_rows(self):
        wizard = self.Wizard.create(
            {
                "name": "Dyn Sheet",
                "datasource_name": "Src",
                "mode_id": self.mode_new.id,
                "import_data": {},
                "dynamic": True,
                "number_of_rows": 7,
            }
        )
        action = wizard.insert_pivot()
        self.assertEqual(action["params"]["import_data"]["dyn_number_of_rows"], 7)

    def test_insert_pivot_add_targets_existing(self):
        spreadsheet = self.env["spreadsheet.spreadsheet"].create({"name": "Existing"})
        wizard = self.Wizard.create(
            {
                "name": "Add",
                "datasource_name": "Src2",
                "mode_id": self.mode_add.id,
                "import_data": {"x": 1},
                "spreadsheet_id": spreadsheet.id,
                "dynamic": True,
                "number_of_rows": 3,
            }
        )
        action = wizard.insert_pivot()
        self.assertEqual(action["params"]["spreadsheet_id"], spreadsheet.id)
        self.assertEqual(action["params"]["import_data"]["name"], "Src2")
        self.assertEqual(action["params"]["import_data"]["dyn_number_of_rows"], 3)
