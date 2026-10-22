from odoo import api, fields, models
from odoo.exceptions import UserError


class FieldLinkingTestOrder(models.Model):
    _name = "field.linking.test.order"
    _description = "Field Linking Test Order"
    _inherit = "spreadsheet.linkable"

    name = fields.Char()
    note = fields.Char()
    state = fields.Selection([("draft", "Draft"), ("done", "Done")], default="draft")
    total = fields.Float(compute="_compute_total", store=True)
    partner_id = fields.Many2one("res.partner")
    line_ids = fields.One2many("field.linking.test.line", "order_id")

    @api.depends("line_ids.price")
    def _compute_total(self):
        for order in self:
            order.total = sum(order.line_ids.mapped("price"))

    def _check_linking_allowed(self):
        self.ensure_one()
        if self.state == "done":
            raise UserError(self.env._("Cannot write values into a done order."))


class FieldLinkingTestLine(models.Model):
    _name = "field.linking.test.line"
    _description = "Field Linking Test Line"

    order_id = fields.Many2one("field.linking.test.order", ondelete="cascade")
    partner_id = fields.Many2one("res.partner")
    label = fields.Char()
    qty = fields.Float()
    price = fields.Float()
    display_type = fields.Char()


class FieldLinkingHookedOrder(models.Model):
    _name = "field.linking.hooked.order"
    _description = "Field Linking Hooked Order"
    _inherit = "spreadsheet.linkable"

    name = fields.Char()
    line_ids = fields.One2many("field.linking.hooked.line", "order_id")

    def _linking_candidates(self, records, segment):
        return records.filtered(lambda line: not line.skip)

    def _linking_label(self, line):
        return line.label

    def _linking_write(self, record, values):
        return record.write({**values, "touched": True})

    def _create_linked_line(self, parent, segment, values):
        return parent.env["field.linking.hooked.line"].create(
            {"order_id": parent.id, "touched": True, **values}
        )


class FieldLinkingHookedLine(models.Model):
    _name = "field.linking.hooked.line"
    _description = "Field Linking Hooked Line"

    order_id = fields.Many2one("field.linking.hooked.order", ondelete="cascade")
    label = fields.Char()
    qty = fields.Float()
    skip = fields.Boolean()
    touched = fields.Boolean()
