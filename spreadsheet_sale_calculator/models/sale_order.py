from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "spreadsheet.linkable"]

    template_calculator_id = fields.Many2one(
        "spreadsheet.spreadsheet",
        string="Quote Calculator Template",
        compute="_compute_template_calculator_id",
        store=True,
        readonly=False,
        copy=False,
        domain=[("link_res_model", "=", False)],
        help="Spreadsheet copied as this order's quote calculator. Defaults to "
        "the one set on the quotation template; pick another to override it.",
    )
    calculator_spreadsheet_id = fields.Many2one(
        "spreadsheet.spreadsheet",
        string="Quote Calculator",
        copy=False,
    )
    show_update_calculator = fields.Boolean(
        string="Has Quote Calculator Template Changed", store=False
    )

    @api.depends("sale_order_template_id")
    def _compute_template_calculator_id(self):
        for order in self:
            order.template_calculator_id = (
                order.sale_order_template_id.quote_calculator_id
            )

    @api.onchange("template_calculator_id")
    def _onchange_template_calculator_id_show_update(self):
        self.show_update_calculator = (
            self._origin.template_calculator_id != self.template_calculator_id
        )

    def _build_calculator_copy(self):
        self.ensure_one()
        return self.template_calculator_id.sudo().copy(
            {
                "name": self.env._("%s Calculator", self.name),
                "owner_id": self.env.user.id,
            }
        )

    def action_open_quote_calculator(self):
        self.ensure_one()
        if not self.calculator_spreadsheet_id:
            if not self.template_calculator_id:
                raise UserError(
                    self.env._(
                        "This order has no quote calculator. Set one on its "
                        "quotation template first."
                    )
                )
            self.calculator_spreadsheet_id = self._build_calculator_copy().id
        self._link_spreadsheet(self.calculator_spreadsheet_id)
        return self.calculator_spreadsheet_id.open_spreadsheet()

    def action_update_quote_calculator(self):
        self.ensure_one()
        stale = self.calculator_spreadsheet_id
        self.calculator_spreadsheet_id = (
            self._build_calculator_copy() if self.template_calculator_id else False
        )
        if stale:
            stale.sudo().unlink()
        self.show_update_calculator = False

    def _check_linking_allowed(self):
        self.ensure_one()
        if self.state == "cancel":
            raise UserError(
                self.env._("Cannot write calculator values into a cancelled order.")
            )
        if self.locked:
            raise UserError(
                self.env._(
                    "This order is locked. Unlock it before writing "
                    "calculator values into its lines."
                )
            )

    def _linking_write(self, record, values):
        # Write price_unit last and alone so the pricelist recompute can't clobber it.
        values = dict(values)
        price = values.pop("price_unit", None)
        if values:
            record.write(values)
        if price is not None:
            record.write({"price_unit": price})
