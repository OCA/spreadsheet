# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"

    spreadsheet_id = fields.Many2one(
        "spreadsheet.spreadsheet",
        string="Quotation Calculator",
        copy=True,
        help="Spreadsheet used as pricing calculator for quotations "
        "created from this template.",
    )

    def action_create_spreadsheet_calculator(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Create Quotation Calculator",
            "res_model": "spreadsheet.quotation.create",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_sale_order_template_id": self.id,
            },
        }

    def action_open_spreadsheet_calculator(self):
        self.ensure_one()
        if self.spreadsheet_id:
            return self.spreadsheet_id.open_spreadsheet()
        return self.action_create_spreadsheet_calculator()
