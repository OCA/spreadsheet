import base64
import io

from odoo_test_helper import FakeModelLoader
from openpyxl import Workbook

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSpreadsheetUploadMixin(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .demo_model import DemoSpreadsheetUploadModel

        cls.loader.update_registry([DemoSpreadsheetUploadModel])

    @staticmethod
    def _generate_sample_xls_data():
        """New method to generate xls data."""
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Sheet1"
        worksheet["A1"] = "Sample XLSX Data"
        worksheet["A2"] = "Demo Data"
        worksheet["A3"] = "This is a sample XLSX file for testing."
        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return base64.b64encode(buffer.read())

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        return super().tearDownClass()

    def test_00_check_xlsx_file_type_valid(self):
        """New method to check valid xlsx file type."""
        record = self.env["demo.spreadsheet.upload"].create(
            {"file_name": "test_file.xlsx"}
        )
        # Assers that file is created successfully.
        self.assertEqual(
            record.file_name, "test_file.xlsx", "File name is not set correctly."
        )

    def test_01_check_xlsx_file_type_invalid(self):
        """New method to check invalid xlsx file type."""
        # Asserts that ValidationError is raised for invalid file type.
        with self.assertRaises(ValidationError):
            self.env["demo.spreadsheet.upload"].create({"file_name": "test_file.txt"})

    def test_02_create_attachment(self):
        """New method to check create attachment from upload file."""
        record = self.env["demo.spreadsheet.upload"].create(
            {
                "file_name": "test_file.xlsx",
                "upload_file": self._generate_sample_xls_data(),
            }
        )
        record.action_create_spreadsheet()
        # Asserts that spreadsheet is created successfully.
        self.assertTrue(record.spreadsheet_id, "Spreadsheet is not created.")
        action = record.action_open_spreadsheet()
        # Asserts that the action returned has the correct spreadsheet ID.
        self.assertEqual(
            action["params"]["spreadsheet_id"],
            record.spreadsheet_id.id,
            "spredsheet is not same.",
        )
