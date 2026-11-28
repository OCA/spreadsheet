from odoo import fields, models


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"

    quote_calculator_id = fields.Many2one(
        "spreadsheet.spreadsheet",
        string="Quote Calculator",
        copy=False,
        domain=[("link_res_model", "=", False)],
    )
