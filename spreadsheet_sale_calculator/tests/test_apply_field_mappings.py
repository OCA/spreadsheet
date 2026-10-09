# Copyright 2026 arielbarreiros96
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0).

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase


class TestApplyFieldMappings(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.product = cls.env["product.product"].create(
            {"name": "Test Product", "list_price": 100.0}
        )
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_uom_qty": 1,
                            "price_unit": 100.0,
                        }
                    ),
                    Command.create({"display_type": "line_section", "name": "Section"}),
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_uom_qty": 2,
                            "price_unit": 50.0,
                        }
                    ),
                ],
            }
        )
        cls.product_lines = cls.order.order_line.filtered(
            lambda line: not line.display_type
        )

    def _line(self, field, position, value):
        return {
            "chain": f"order_line.{field}",
            "selectors": {"order_line": position},
            "value": value,
        }

    def test_write_value_to_line(self):
        result = self.order.apply_field_mappings([self._line("price_unit", 1, 250.0)])
        self.assertEqual(result, {"updated": 1, "created": 0})
        self.assertEqual(self.product_lines[0].price_unit, 250.0)

    def test_position_skips_section_lines(self):
        self.order.apply_field_mappings([self._line("product_uom_qty", 2, 9)])
        self.assertEqual(self.product_lines[1].product_uom_qty, 9)
        self.assertEqual(self.product_lines[0].product_uom_qty, 1)

    def test_price_unit_survives_quantity_change(self):
        self.order.apply_field_mappings([self._line("price_unit", 1, 250.0)])
        self.product_lines[0].product_uom_qty = 5
        self.assertEqual(self.product_lines[0].price_unit, 250.0)

    def test_readonly_line_field_is_skipped(self):
        result = self.order.apply_field_mappings(
            [self._line("price_subtotal", 1, 999.0)]
        )
        self.assertEqual(result, {"updated": 0, "created": 0})

    def test_creates_new_line_beyond_count(self):
        result = self.order.apply_field_mappings(
            [
                self._line("product_id", 3, self.product.id),
                self._line("product_uom_qty", 3, 4),
                self._line("price_unit", 3, 75.0),
            ]
        )
        self.assertEqual(result, {"updated": 0, "created": 1})
        lines = self.order.order_line.filtered(lambda line: not line.display_type)
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[2].product_id, self.product)
        self.assertEqual(lines[2].product_uom_qty, 4)
        self.assertEqual(lines[2].price_unit, 75.0)

    def test_locked_order_raises(self):
        self.order.locked = True
        with self.assertRaises(UserError):
            self.order.apply_field_mappings([self._line("price_unit", 1, 1.0)])

    def test_cancelled_order_raises(self):
        self.order.state = "cancel"
        with self.assertRaises(UserError):
            self.order.apply_field_mappings([self._line("price_unit", 1, 1.0)])


class TestCalculatorSpreadsheet(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref(
            "sale_management.group_sale_order_template"
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.product = cls.env["product.product"].create({"name": "Test Product"})

    def _make_template(self):
        return self.env["sale.order.template"].create(
            {
                "name": "Test Template",
                "sale_order_template_line_ids": [
                    Command.create(
                        {"product_id": self.product.id, "product_uom_qty": 1}
                    ),
                    Command.create({"display_type": "line_section", "name": "Section"}),
                    Command.create(
                        {"product_id": self.product.id, "product_uom_qty": 2}
                    ),
                ],
            }
        )

    def _make_calculator(self):
        return self.env["spreadsheet.spreadsheet"].create({"name": "Calc"})

    def test_context_non_calculator(self):
        context = self._make_calculator().get_linking_context()
        self.assertFalse(context["isLinkable"])
        self.assertFalse(context["writable"])

    def test_context_from_order(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create({"product_id": self.product.id}),
                    Command.create({"display_type": "line_section", "name": "S"}),
                    Command.create({"product_id": self.product.id}),
                ],
            }
        )
        calculator = self._make_calculator()
        order.calculator_spreadsheet_id = calculator
        order._link_spreadsheet(calculator)
        context = calculator.get_linking_context()
        self.assertTrue(context["isLinkable"])
        self.assertTrue(context["writable"])
        self.assertEqual(context["resId"], order.id)
        self.assertEqual(context["recordName"], order.display_name)
        selectors = calculator.get_link_selectors("order_line.price_unit")
        positions = [line["position"] for line in selectors[0]["labels"]]
        self.assertEqual(positions, [1, 2])

    def test_context_from_template(self):
        template = self._make_template()
        calculator = self._make_calculator()
        template.quote_calculator_id = calculator
        context = calculator.get_linking_context()
        self.assertTrue(context["isLinkable"])
        self.assertFalse(context["writable"])
        self.assertFalse(context["resId"])
        self.assertEqual(context["model"], "sale.order")
        selectors = calculator.get_link_selectors("order_line.price_unit")
        self.assertEqual(selectors[0]["segment"], "order_line")
        self.assertEqual(selectors[0]["labels"], [])

    def test_template_calculator_defaults_from_quotation_template(self):
        template = self._make_template()
        calculator = self._make_calculator()
        template.quote_calculator_id = calculator
        order = self.env["sale.order"].create(
            {"partner_id": self.partner.id, "sale_order_template_id": template.id}
        )
        self.assertEqual(order.template_calculator_id, calculator)

    def test_selecting_template_calculator_directly(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        calculator = self._make_calculator()
        order.template_calculator_id = calculator
        action = order.action_open_quote_calculator()
        self.assertTrue(order.calculator_spreadsheet_id)
        self.assertNotEqual(order.calculator_spreadsheet_id, calculator)
        self.assertEqual(
            action["params"]["spreadsheet_id"], order.calculator_spreadsheet_id.id
        )

    def test_changing_template_calculator_keeps_copy(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        order.template_calculator_id = self._make_calculator()
        order.action_open_quote_calculator()
        copy = order.calculator_spreadsheet_id
        self.assertTrue(copy)
        order.template_calculator_id = self._make_calculator()
        self.assertEqual(order.calculator_spreadsheet_id, copy)

    def test_open_quote_calculator_without_template_raises(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        with self.assertRaises(UserError):
            order.action_open_quote_calculator()

    def test_open_quote_calculator_copies_template_calculator(self):
        template = self._make_template()
        template.quote_calculator_id = self._make_calculator()
        order = self.env["sale.order"].create(
            {"partner_id": self.partner.id, "sale_order_template_id": template.id}
        )
        action = order.action_open_quote_calculator()
        self.assertTrue(order.calculator_spreadsheet_id)
        self.assertNotEqual(
            order.calculator_spreadsheet_id, template.quote_calculator_id
        )
        self.assertEqual(order.calculator_spreadsheet_id.owner_id, self.env.user)
        self.assertEqual(action["tag"], "action_spreadsheet_oca")
        self.assertEqual(
            action["params"]["spreadsheet_id"], order.calculator_spreadsheet_id.id
        )

    def test_open_existing_calculator_reuses_it(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        calculator = self._make_calculator()
        order.calculator_spreadsheet_id = calculator
        action = order.action_open_quote_calculator()
        self.assertEqual(order.calculator_spreadsheet_id, calculator)
        self.assertEqual(action["params"]["spreadsheet_id"], calculator.id)

    def test_changing_template_keeps_calculator(self):
        template = self._make_template()
        template.quote_calculator_id = self._make_calculator()
        order = self.env["sale.order"].create(
            {"partner_id": self.partner.id, "sale_order_template_id": template.id}
        )
        order.action_open_quote_calculator()
        copy = order.calculator_spreadsheet_id
        self.assertTrue(copy)
        order.sale_order_template_id = self._make_template()
        self.assertEqual(order.calculator_spreadsheet_id, copy)

    def test_changing_template_offers_rebuild(self):
        template = self._make_template()
        template.quote_calculator_id = self._make_calculator()
        order = self.env["sale.order"].create(
            {"partner_id": self.partner.id, "sale_order_template_id": template.id}
        )
        order.action_open_quote_calculator()
        self.assertTrue(order.calculator_spreadsheet_id)
        other = self._make_template()
        other.quote_calculator_id = self._make_calculator()
        with Form(order) as form:
            self.assertFalse(form.show_update_calculator)
            form.sale_order_template_id = other
            self.assertTrue(form.show_update_calculator)
        self.assertTrue(order.calculator_spreadsheet_id)

    def test_changing_template_offers_rebuild_without_existing_copy(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        with Form(order) as form:
            self.assertFalse(form.show_update_calculator)
            form.template_calculator_id = self._make_calculator()
            self.assertTrue(form.show_update_calculator)

    def test_rebuild_calculator_replaces_copy(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        order.template_calculator_id = self._make_calculator()
        order.action_open_quote_calculator()
        stale = order.calculator_spreadsheet_id
        self.assertTrue(stale)
        order.template_calculator_id = self._make_calculator()
        order.show_update_calculator = True
        order.action_update_quote_calculator()
        self.assertFalse(stale.exists())
        self.assertTrue(order.calculator_spreadsheet_id)
        self.assertNotEqual(order.calculator_spreadsheet_id, stale)
        self.assertFalse(order.show_update_calculator)

    def test_rebuild_leaves_calculator_that_re_offers_rebuild(self):
        template = self._make_template()
        template.quote_calculator_id = self._make_calculator()
        order = self.env["sale.order"].create(
            {"partner_id": self.partner.id, "sale_order_template_id": template.id}
        )
        order.action_open_quote_calculator()
        order.action_update_quote_calculator()
        self.assertTrue(order.calculator_spreadsheet_id)
        other = self._make_template()
        other.quote_calculator_id = self._make_calculator()
        with Form(order) as form:
            form.sale_order_template_id = other
            self.assertTrue(form.show_update_calculator)

    def test_setting_same_template_keeps_calculator(self):
        template = self._make_template()
        template.quote_calculator_id = self._make_calculator()
        order = self.env["sale.order"].create(
            {"partner_id": self.partner.id, "sale_order_template_id": template.id}
        )
        order.action_open_quote_calculator()
        calculator = order.calculator_spreadsheet_id
        self.assertTrue(calculator)
        order.write({"sale_order_template_id": template.id})
        self.assertEqual(order.calculator_spreadsheet_id, calculator)

    def test_setting_template_without_calculator_is_noop(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        template = self._make_template()
        order.write({"sale_order_template_id": template.id})
        self.assertFalse(order.calculator_spreadsheet_id)
