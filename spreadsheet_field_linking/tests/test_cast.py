# Copyright 2026 arielbarreiros96
# License AGPL-3.0 or later (https://www.gnu.org/licenses/AGPL-3.0).

from datetime import date, datetime
from types import SimpleNamespace

from odoo import Command
from odoo.tests.common import TransactionCase

from odoo.addons.spreadsheet_field_linking.models.spreadsheet_linkable import _cast


def cast(ftype, value):
    return _cast(SimpleNamespace(type=ftype), value)


class TestCast(TransactionCase):
    def test_numeric(self):
        self.assertEqual(cast("float", "3.5"), 3.5)
        self.assertEqual(cast("float", 2), 2.0)
        self.assertEqual(cast("monetary", "10"), 10.0)
        self.assertEqual(cast("integer", 2.7), 2)
        self.assertEqual(cast("integer", "4"), 4)

    def test_numeric_zero_is_written(self):
        self.assertEqual(cast("float", 0), 0.0)
        self.assertEqual(cast("integer", 0), 0)

    def test_uncastable_numbers_are_skipped(self):
        self.assertIsNone(cast("float", "abc"))
        self.assertIsNone(cast("integer", "abc"))

    def test_boolean(self):
        for falsy in ("FALSE", "false", "no", "n", "0", 0):
            self.assertIs(cast("boolean", falsy), False, falsy)
        for truthy in ("TRUE", "yes", "1", 1, "anything"):
            self.assertIs(cast("boolean", truthy), True, truthy)

    def test_text(self):
        self.assertEqual(cast("char", 12), "12")
        self.assertEqual(cast("text", "hello"), "hello")
        self.assertEqual(cast("html", 3.5), "3.5")

    def test_selection(self):
        self.assertEqual(cast("selection", 1.0), "1")
        self.assertEqual(cast("selection", 2), "2")
        self.assertEqual(cast("selection", "draft"), "draft")

    def test_date_and_datetime_from_serial(self):
        self.assertEqual(cast("date", 45292), date(2024, 1, 1))
        self.assertEqual(cast("datetime", 45292.25), datetime(2024, 1, 1, 6, 0, 0))

    def test_date_and_datetime_from_string(self):
        self.assertEqual(
            cast("datetime", "2024-01-01 06:00:00"), datetime(2024, 1, 1, 6, 0, 0)
        )
        self.assertEqual(cast("date", "2024-01-01 00:00:00"), date(2024, 1, 1))
        self.assertIsNone(cast("datetime", "not-a-date"))

    def test_many2one(self):
        self.assertEqual(cast("many2one", 7), 7)
        self.assertEqual(cast("many2one", 7.0), 7)
        self.assertIsNone(cast("many2one", 7.4))

    def test_x2many_ids(self):
        expected = [Command.set([1, 2, 3])]
        self.assertEqual(cast("one2many", "1,2,3"), expected)
        self.assertEqual(cast("many2many", [1, 2, 3]), expected)
        self.assertIsNone(cast("many2many", "abc"))

    def test_empty_clears_scalars(self):
        for ftype in ("float", "integer", "char", "boolean", "date", "many2one"):
            self.assertIs(cast(ftype, ""), False, ftype)
            self.assertIs(cast(ftype, None), False, ftype)

    def test_empty_clears_x2many(self):
        self.assertEqual(cast("one2many", ""), [Command.clear()])
        self.assertEqual(cast("many2many", None), [Command.clear()])

    def test_unhandled_type_is_skipped(self):
        self.assertIsNone(cast("binary", "x"))
        self.assertIsNone(cast("json", {"a": 1}))
