# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSpreadsheetQuotation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "list_price": 100.0,
            }
        )
        cls.template = cls.env["sale.order.template"].create(
            {
                "name": "Test Template",
                "sale_order_template_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_uom_qty": 5,
                            "product_uom_id": cls.product.uom_id.id,
                        },
                    )
                ],
            }
        )

    def _create_calculator(self, template=None, name="My Calculator", lines=10):
        template = template or self.template
        wizard = (
            self.env["spreadsheet.quotation.create"]
            .with_context(default_sale_order_template_id=template.id)
            .create(
                {
                    "name": name,
                    "line_count": lines,
                    "sale_order_template_id": template.id,
                }
            )
        )
        return wizard.action_create()

    def test_wizard_creates_calculator(self):
        """The wizard should create a spreadsheet linked to the template."""
        self.assertFalse(self.template.spreadsheet_id)
        action = self._create_calculator()

        self.assertTrue(self.template.spreadsheet_id)
        self.assertEqual(self.template.spreadsheet_id.name, "My Calculator")
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "action_spreadsheet_oca")

    def test_wizard_spreadsheet_contains_list(self):
        """The spreadsheet should contain a list definition for sale.order.line."""
        self._create_calculator()

        data = self.template.spreadsheet_id.spreadsheet_raw
        if isinstance(data, str):
            data = json.loads(data)

        self.assertIn("lists", data)
        list_def = data["lists"].get("1")
        self.assertIsNotNone(list_def)
        self.assertEqual(list_def["model"], "sale.order.line")
        self.assertIn("product_id", list_def["columns"])
        self.assertIn("product_uom_qty", list_def["columns"])
        self.assertIn("price_unit", list_def["columns"])

    def test_wizard_list_filters_display_type(self):
        """The list domain should exclude section/note lines."""
        self._create_calculator()

        data = self.template.spreadsheet_id.spreadsheet_raw
        if isinstance(data, str):
            data = json.loads(data)

        list_def = data["lists"]["1"]
        self.assertIn(["display_type", "=", False], list_def["domain"])

    def test_wizard_spreadsheet_contains_global_filter(self):
        """The spreadsheet should contain a global filter for sale.order."""
        self._create_calculator()

        data = self.template.spreadsheet_id.spreadsheet_raw
        if isinstance(data, str):
            data = json.loads(data)

        self.assertIn("globalFilters", data)
        filters = data["globalFilters"]
        self.assertEqual(len(filters), 1)
        self.assertEqual(filters[0]["type"], "relation")
        self.assertEqual(filters[0]["modelName"], "sale.order")

    def test_wizard_field_matching(self):
        """The list should have field matching linking it to the global filter."""
        self._create_calculator()

        data = self.template.spreadsheet_id.spreadsheet_raw
        if isinstance(data, str):
            data = json.loads(data)

        list_def = data["lists"]["1"]
        filter_id = data["globalFilters"][0]["id"]
        self.assertIn(filter_id, list_def["fieldMatching"])
        matching = list_def["fieldMatching"][filter_id]
        self.assertEqual(matching["chain"], "order_id")
        self.assertEqual(matching["type"], "many2one")

    def test_wizard_spreadsheet_cells_have_formulas(self):
        """The spreadsheet should contain ODOO.LIST formulas in cells."""
        self._create_calculator(lines=5)

        data = self.template.spreadsheet_id.spreadsheet_raw
        if isinstance(data, str):
            data = json.loads(data)

        sheets = data.get("sheets", [])
        self.assertTrue(sheets)
        cells = sheets[0].get("cells", {})
        self.assertIn("A1", cells)
        self.assertIn("ODOO.LIST.HEADER", cells["A1"]["content"])
        self.assertIn("A2", cells)
        self.assertIn("ODOO.LIST", cells["A2"]["content"])

    def test_template_application_copies_spreadsheet(self):
        """Applying a template with a calculator to a SO should copy it."""
        self._create_calculator()

        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        order.sale_order_template_id = self.template
        order._onchange_sale_order_template_id()
        order._onchange_sale_order_template_id_spreadsheet()

        self.assertTrue(order.spreadsheet_id)
        self.assertNotEqual(order.spreadsheet_id, self.template.spreadsheet_id)

    def test_copied_spreadsheet_has_filter_with_order_id(self):
        """The copied spreadsheet should have the global filter set to the SO id."""
        self._create_calculator()

        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        order.sale_order_template_id = self.template
        order._onchange_sale_order_template_id()
        order._onchange_sale_order_template_id_spreadsheet()

        data = order.spreadsheet_id.spreadsheet_raw
        if isinstance(data, str):
            data = json.loads(data)

        filters = data.get("globalFilters", [])
        so_filter = next(
            (f for f in filters if f.get("modelName") == "sale.order"),
            None,
        )
        self.assertIsNotNone(so_filter)
        self.assertEqual(so_filter["defaultValue"], [order.id])

    def test_template_without_spreadsheet(self):
        """Applying a template without calculator should not create one."""
        template_no_calc = self.env["sale.order.template"].create(
            {"name": "No Calculator Template"}
        )
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        order.sale_order_template_id = template_no_calc
        order._onchange_sale_order_template_id()
        order._onchange_sale_order_template_id_spreadsheet()

        self.assertFalse(order.spreadsheet_id)

    def test_clearing_template_clears_spreadsheet(self):
        """Removing the template should clear the spreadsheet reference."""
        self._create_calculator()

        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        order.sale_order_template_id = self.template
        order._onchange_sale_order_template_id()
        order._onchange_sale_order_template_id_spreadsheet()
        self.assertTrue(order.spreadsheet_id)

        order.sale_order_template_id = False
        order._onchange_sale_order_template_id_spreadsheet()
        self.assertFalse(order.spreadsheet_id)

    def test_open_spreadsheet_action(self):
        """Opening the calculator should return a client action."""
        self._create_calculator()

        action = self.template.action_open_spreadsheet_calculator()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "action_spreadsheet_oca")

    def test_col_index_to_letter(self):
        """Column index conversion should produce correct letters."""
        wizard = self.env["spreadsheet.quotation.create"]
        self.assertEqual(wizard._col_index_to_letter(0), "A")
        self.assertEqual(wizard._col_index_to_letter(1), "B")
        self.assertEqual(wizard._col_index_to_letter(25), "Z")
        self.assertEqual(wizard._col_index_to_letter(26), "AA")
        self.assertEqual(wizard._col_index_to_letter(27), "AB")

    def test_has_spreadsheet_computed(self):
        """has_spreadsheet should reflect the presence of spreadsheet_id."""
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        self.assertFalse(order.has_spreadsheet)

        self._create_calculator()

        order.sale_order_template_id = self.template
        order._onchange_sale_order_template_id()
        order._onchange_sale_order_template_id_spreadsheet()

        self.assertTrue(order.has_spreadsheet)

    def _create_order_with_line(self):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                        },
                    )
                ],
            }
        )

    def test_sync_allowed_in_draft(self):
        """Spreadsheet sync should update lines on draft quotations."""
        order = self._create_order_with_line()
        line = order.order_line[0]
        commands = [[1, line.id, {"product_uom_qty": 10}]]
        order.action_sync_spreadsheet_order_lines(commands)
        self.assertEqual(line.product_uom_qty, 10)

    def test_sync_allowed_in_sent(self):
        """Spreadsheet sync should update lines on sent quotations."""
        order = self._create_order_with_line()
        order.write({"state": "sent"})
        line = order.order_line[0]
        commands = [[1, line.id, {"product_uom_qty": 8}]]
        order.action_sync_spreadsheet_order_lines(commands)
        self.assertEqual(line.product_uom_qty, 8)

    def test_sync_blocked_in_sale(self):
        """Spreadsheet sync should be blocked on confirmed sales orders."""
        order = self._create_order_with_line()
        order.action_confirm()
        line = order.order_line[0]
        commands = [[1, line.id, {"product_uom_qty": 10}]]
        with self.assertRaises(UserError):
            order.action_sync_spreadsheet_order_lines(commands)

    def test_sync_blocked_in_cancel(self):
        """Spreadsheet sync should be blocked on cancelled quotations."""
        order = self._create_order_with_line()
        order.action_cancel()
        line = order.order_line[0]
        commands = [[1, line.id, {"product_uom_qty": 10}]]
        with self.assertRaises(UserError):
            order.action_sync_spreadsheet_order_lines(commands)
