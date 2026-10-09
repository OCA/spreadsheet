# Copyright 2026 arielbarreiros96
# License AGPL-3.0 or later (https://www.gnu.org/licenses/AGPL-3.0).

from odoo import Command
from odoo.exceptions import UserError
from odoo.orm.model_classes import add_to_registry
from odoo.tests.common import TransactionCase


class TestApplyFieldMappings(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from .test_models import (
            FieldLinkingHookedLine,
            FieldLinkingHookedOrder,
            FieldLinkingTestLine,
            FieldLinkingTestOrder,
        )

        registered = (
            FieldLinkingTestOrder,
            FieldLinkingTestLine,
            FieldLinkingHookedOrder,
            FieldLinkingHookedLine,
        )
        names = [model._name for model in registered]
        for model in registered:
            add_to_registry(cls.registry, model)
        cls.registry._setup_models__(cls.env.cr, names)
        cls.registry.init_models(cls.env.cr, names, {"models_to_check": True})
        for name in names:
            cls.addClassCleanup(cls.registry.__delitem__, name)

        cls.partner = cls.env["res.partner"].create({"name": "Partner"})
        cls.other_partner = cls.env["res.partner"].create({"name": "Other"})
        cls.Order = cls.env["field.linking.test.order"]
        cls.order = cls.Order.create(
            {
                "name": "Order",
                "partner_id": cls.partner.id,
                "line_ids": [
                    Command.create({"label": "First", "qty": 1, "price": 100.0}),
                    Command.create({"label": "S", "display_type": "line_section"}),
                    Command.create({"label": "Second", "qty": 2, "price": 50.0}),
                ],
            }
        )
        cls.lines = cls.order.line_ids.filtered(lambda line: not line.display_type)
        cls.hooked = cls.env["field.linking.hooked.order"].create(
            {"name": "H", "line_ids": [Command.create({"label": "L1", "qty": 1})]}
        )

    def _line(self, field, position, value):
        return {
            "chain": f"line_ids.{field}",
            "selectors": {"line_ids": position},
            "value": value,
        }

    def test_write_root_field(self):
        result = self.order.apply_field_mappings([{"chain": "note", "value": "hello"}])
        self.assertEqual(result, {"updated": 1, "created": 0})
        self.assertEqual(self.order.note, "hello")

    def test_readonly_field_is_skipped(self):
        result = self.order.apply_field_mappings([{"chain": "total", "value": 5.0}])
        self.assertEqual(result, {"updated": 0, "created": 0})
        self.assertEqual(self.order.total, 150.0)

    def test_unknown_field_is_skipped(self):
        result = self.order.apply_field_mappings([{"chain": "nope", "value": 1}])
        self.assertEqual(result, {"updated": 0, "created": 0})

    def test_empty_cell_clears_field(self):
        self.order.apply_field_mappings([{"chain": "note", "value": ""}])
        self.assertFalse(self.order.note)

    def test_write_line_by_position(self):
        result = self.order.apply_field_mappings([self._line("price", 1, 250.0)])
        self.assertEqual(result, {"updated": 1, "created": 0})
        self.assertEqual(self.lines[0].price, 250.0)

    def test_position_skips_section_lines(self):
        self.order.apply_field_mappings([self._line("qty", 2, 9)])
        self.assertEqual(self.lines[1].qty, 9)
        self.assertEqual(self.lines[0].qty, 1)

    def test_tagged_real_lines_are_counted(self):
        # Reproduces account.move.line semantics: display_type is required and
        # set on real lines ("product"), not only on sections. Only the layout
        # markers (section/note) must be skipped, never every tagged line.
        order = self.Order.create(
            {
                "name": "Entry",
                "line_ids": [
                    Command.create({"label": "Sec", "display_type": "line_section"}),
                    Command.create(
                        {"label": "Real", "qty": 1, "display_type": "product"}
                    ),
                ],
            }
        )
        selectors = order._linking_selectors("line_ids.qty")
        positions = [line["position"] for line in selectors[0]["labels"]]
        self.assertEqual(positions, [1])
        result = order.apply_field_mappings(
            [{"chain": "line_ids.qty", "selectors": {"line_ids": 1}, "value": 7.0}]
        )
        self.assertEqual(result, {"updated": 1, "created": 0})
        real = order.line_ids.filtered(lambda line: line.display_type == "product")
        self.assertEqual(real.qty, 7.0)

    def test_grouped_leaves_write_one_line(self):
        result = self.order.apply_field_mappings(
            [self._line("price", 1, 250.0), self._line("qty", 1, 3)]
        )
        self.assertEqual(result, {"updated": 1, "created": 0})
        self.assertEqual(self.lines[0].price, 250.0)
        self.assertEqual(self.lines[0].qty, 3)

    def test_creates_line_beyond_count(self):
        result = self.order.apply_field_mappings(
            [
                self._line("partner_id", 3, self.other_partner.id),
                self._line("qty", 3, 4),
                self._line("price", 3, 75.0),
            ]
        )
        self.assertEqual(result, {"updated": 0, "created": 1})
        lines = self.order.line_ids.filtered(lambda line: not line.display_type)
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[2].partner_id, self.other_partner)
        self.assertEqual(lines[2].qty, 4)
        self.assertEqual(lines[2].price, 75.0)

    def test_new_line_without_writable_values_is_skipped(self):
        result = self.order.apply_field_mappings([self._line("nope", 3, 4)])
        self.assertEqual(result, {"updated": 0, "created": 0})

    def test_invalid_selector_is_skipped(self):
        result = self.order.apply_field_mappings(
            [{"chain": "line_ids.price", "selectors": {"line_ids": 0}, "value": 9.0}]
        )
        self.assertEqual(result, {"updated": 0, "created": 0})

    def test_write_through_many2one(self):
        result = self.order.apply_field_mappings(
            [{"chain": "partner_id.ref", "value": "REF-42"}]
        )
        self.assertEqual(result, {"updated": 1, "created": 0})
        self.assertEqual(self.partner.ref, "REF-42")

    def test_empty_many2one_is_skipped(self):
        self.order.partner_id = False
        result = self.order.apply_field_mappings(
            [{"chain": "partner_id.ref", "value": "x"}]
        )
        self.assertEqual(result, {"updated": 0, "created": 0})

    def test_state_guard_raises(self):
        self.order.state = "done"
        with self.assertRaises(UserError):
            self.order.apply_field_mappings([{"chain": "note", "value": "x"}])

    def test_linking_context(self):
        context = self.order._linking_context()
        self.assertTrue(context["isLinkable"])
        self.assertEqual(context["model"], "field.linking.test.order")
        self.assertEqual(context["resId"], self.order.id)
        self.assertEqual(context["recordName"], self.order.display_name)

    def test_linking_selectors_for_line_chain(self):
        selectors = self.order._linking_selectors("line_ids.price")
        self.assertEqual(len(selectors), 1)
        self.assertEqual(selectors[0]["segment"], "line_ids")
        positions = [line["position"] for line in selectors[0]["labels"]]
        self.assertEqual(positions, [1, 2])

    def test_linking_selectors_for_root_field(self):
        self.assertEqual(self.order._linking_selectors("note"), [])

    def test_link_spreadsheet_sets_reference(self):
        sheet = self.env["spreadsheet.spreadsheet"].create({"name": "S"})
        self.order._link_spreadsheet(sheet)
        self.assertEqual(sheet.link_res_model, self.order._name)
        self.assertEqual(sheet.link_res_id, self.order.id)

    def test_duplicate_drops_the_link(self):
        sheet = self.env["spreadsheet.spreadsheet"].create({"name": "S"})
        self.order._link_spreadsheet(sheet)
        copy = sheet.copy()
        self.assertFalse(copy.link_res_model)
        self.assertFalse(copy.link_res_id)
        context = copy.get_linking_context()
        self.assertFalse(context["isLinkable"])

    def test_context_resolves_through_reference(self):
        sheet = self.env["spreadsheet.spreadsheet"].create({"name": "S"})
        self.order._link_spreadsheet(sheet)
        context = sheet.get_linking_context()
        self.assertTrue(context["writable"])
        self.assertEqual(context["resId"], self.order.id)

    def test_get_link_selectors_through_reference(self):
        sheet = self.env["spreadsheet.spreadsheet"].create({"name": "S"})
        self.order._link_spreadsheet(sheet)
        selectors = sheet.get_link_selectors("line_ids.price")
        positions = [line["position"] for line in selectors[0]["labels"]]
        self.assertEqual(positions, [1, 2])

    def test_write_resolves_through_reference(self):
        sheet = self.env["spreadsheet.spreadsheet"].create({"name": "S"})
        self.order._link_spreadsheet(sheet)
        result = sheet.write_field_mappings([{"chain": "note", "value": "hi"}])
        self.assertEqual(result, {"updated": 1, "created": 0})
        self.assertEqual(self.order.note, "hi")

    def test_uncastable_value_skips_the_field(self):
        result = self.order.apply_field_mappings([self._line("qty", 1, "abc")])
        self.assertEqual(result, {"updated": 0, "created": 0})
        self.assertEqual(self.lines[0].qty, 1)

    def test_mapping_without_chain_is_skipped(self):
        result = self.order.apply_field_mappings([{"value": 5}])
        self.assertEqual(result, {"updated": 0, "created": 0})

    def test_unknown_path_segment_is_skipped(self):
        result = self.order.apply_field_mappings(
            [{"chain": "nope.qty", "selectors": {"nope": 1}, "value": 4}]
        )
        self.assertEqual(result, {"updated": 0, "created": 0})

    def test_selectors_break_on_unknown_segment(self):
        self.assertEqual(self.order._linking_selectors("nope.qty"), [])

    def test_selectors_walk_through_many2one(self):
        self.assertEqual(self.order._linking_selectors("partner_id.name"), [])

    def test_link_spreadsheet_is_idempotent(self):
        sheet = self.env["spreadsheet.spreadsheet"].create({"name": "S"})
        self.order._link_spreadsheet(sheet)
        self.order._link_spreadsheet(sheet)
        self.assertEqual(sheet.link_res_model, self.order._name)
        self.assertEqual(sheet.link_res_id, self.order.id)

    def test_candidates_and_label_hooks_shape_selectors(self):
        self.hooked.line_ids = [
            Command.create({"label": "Keep", "qty": 2}),
            Command.create({"label": "Drop", "qty": 3, "skip": True}),
            Command.create({"label": False, "qty": 4}),
        ]
        labels = [
            line["label"]
            for line in self.hooked._linking_selectors("line_ids.qty")[0]["labels"]
        ]
        self.assertNotIn("Drop", labels)
        self.assertEqual(labels[:2], ["L1", "Keep"])
        self.assertTrue(labels[2])

    def test_write_hook_marks_the_line(self):
        result = self.hooked.apply_field_mappings(
            [{"chain": "line_ids.qty", "selectors": {"line_ids": 1}, "value": 9.0}]
        )
        self.assertEqual(result, {"updated": 1, "created": 0})
        self.assertTrue(self.hooked.line_ids[0].touched)
        self.assertEqual(self.hooked.line_ids[0].qty, 9.0)

    def test_create_hook_builds_the_line(self):
        result = self.hooked.apply_field_mappings(
            [{"chain": "line_ids.qty", "selectors": {"line_ids": 2}, "value": 7.0}]
        )
        self.assertEqual(result, {"updated": 0, "created": 1})
        created = self.hooked.line_ids.filtered(lambda line: line.touched)
        self.assertEqual(created.qty, 7.0)


class TestSpreadsheetBridge(TransactionCase):
    def test_context_without_target_is_not_linkable(self):
        spreadsheet = self.env["spreadsheet.spreadsheet"].create({"name": "S"})
        context = spreadsheet.get_linking_context()
        self.assertFalse(context["isLinkable"])
        self.assertFalse(context["writable"])

    def test_selectors_without_target_is_empty(self):
        spreadsheet = self.env["spreadsheet.spreadsheet"].create({"name": "S"})
        self.assertEqual(spreadsheet.get_link_selectors("line_ids.price"), [])

    def test_write_without_target_is_noop(self):
        spreadsheet = self.env["spreadsheet.spreadsheet"].create({"name": "S"})
        result = spreadsheet.write_field_mappings([{"chain": "note", "value": "x"}])
        self.assertEqual(result, {"updated": 0, "created": 0})


class TestGenericLinking(TransactionCase):
    """Any concrete record is writable without inheriting the mixin."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Partner"})
        cls.sheet = cls.env["spreadsheet.spreadsheet"].create({"name": "S"})
        cls.sheet.write(
            {"link_res_model": "res.partner", "link_res_id": cls.partner.id}
        )

    def test_context_resolves_for_non_mixin_model(self):
        context = self.sheet.get_linking_context()
        self.assertTrue(context["isLinkable"])
        self.assertTrue(context["writable"])
        self.assertEqual(context["model"], "res.partner")
        self.assertEqual(context["resId"], self.partner.id)

    def test_write_root_field(self):
        result = self.sheet.write_field_mappings([{"chain": "ref", "value": "REF-1"}])
        self.assertEqual(result, {"updated": 1, "created": 0})
        self.assertEqual(self.partner.ref, "REF-1")

    def test_readonly_field_is_skipped(self):
        result = self.sheet.write_field_mappings(
            [{"chain": "display_name", "value": "Hacked"}]
        )
        self.assertEqual(result, {"updated": 0, "created": 0})
        self.assertNotEqual(self.partner.display_name, "Hacked")

    def test_creates_line_through_one2many(self):
        result = self.sheet.write_field_mappings(
            [
                {
                    "chain": "child_ids.name",
                    "selectors": {"child_ids": 1},
                    "value": "Child",
                }
            ]
        )
        self.assertEqual(result, {"updated": 0, "created": 1})
        self.assertIn("Child", self.partner.child_ids.mapped("name"))

    def test_many2many_beyond_count_is_not_created(self):
        result = self.sheet.write_field_mappings(
            [
                {
                    "chain": "category_id.name",
                    "selectors": {"category_id": 2},
                    "value": "X",
                }
            ]
        )
        self.assertEqual(result, {"updated": 0, "created": 0})


class TestLinkTarget(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Partner"})
        cls.sheet = cls.env["spreadsheet.spreadsheet"].create({"name": "S"})

    def test_set_link_target_binds_the_record(self):
        context = self.sheet.set_link_target("res.partner", self.partner.id)
        self.assertEqual(self.sheet.link_res_model, "res.partner")
        self.assertEqual(self.sheet.link_res_id, self.partner.id)
        # Returns the fresh context (not a reopen action) so the client can
        # refresh in place without racing the collaborative session.
        self.assertTrue(context["isLinkable"])
        self.assertEqual(context["resId"], self.partner.id)
        self.assertEqual(context["spreadsheetId"], self.sheet.id)

    def test_set_link_target_clears_the_link(self):
        self.sheet.set_link_target("res.partner", self.partner.id)
        self.sheet.set_link_target()
        self.assertFalse(self.sheet.link_res_model)
        self.assertFalse(self.sheet.link_res_id)
        self.assertFalse(self.sheet.get_linking_context()["isLinkable"])

    def test_linkable_models_excludes_transient_and_abstract(self):
        names = self.env["spreadsheet.spreadsheet"].get_linkable_models()
        self.assertIn("res.partner", names)
        self.assertNotIn("spreadsheet.linkable", names)
        self.assertFalse(any(self.env[name]._transient for name in names))

    def test_linkable_models_respects_write_access(self):
        user = self.env["res.users"].create(
            {
                "name": "Portal",
                "login": "sfl_portal",
                "group_ids": [Command.link(self.env.ref("base.group_portal").id)],
            }
        )
        sheet = self.env["spreadsheet.spreadsheet"].with_user(user)
        self.assertNotIn("ir.model", sheet.get_linkable_models())

    def test_dangling_reference_is_not_linkable(self):
        self.sheet.write(
            {"link_res_model": "res.partner", "link_res_id": self.partner.id}
        )
        self.partner.unlink()
        self.assertFalse(self.sheet.get_linking_context()["isLinkable"])
