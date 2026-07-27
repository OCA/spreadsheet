# Copyright 2026 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestSpreadsheetFilename(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Spreadsheet = cls.env["spreadsheet.spreadsheet"]

    def test_filename_single_record(self):
        spreadsheet = self.Spreadsheet.create({"name": "Budget"})
        self.assertEqual(spreadsheet.filename, "Budget.json")

    def test_filename_is_computed_per_record(self):
        """Each record must get its own name, not the first record's.

        _compute_filename used to read ``self.name`` while iterating over
        ``self``, which raises a singleton error on a multi-record set.
        """
        alpha = self.Spreadsheet.create({"name": "Alpha"})
        beta = self.Spreadsheet.create({"name": "Beta"})

        both = alpha | beta

        self.assertEqual(both.mapped("filename"), ["Alpha.json", "Beta.json"])
