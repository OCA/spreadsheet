from odoo import models


class SpreadsheetSpreadsheet(models.Model):
    _inherit = "spreadsheet.spreadsheet"

    def _get_calculator_template(self):
        self.ensure_one()
        return self.env["sale.order.template"].search(
            [("quote_calculator_id", "=", self.id)], limit=1
        )

    def _get_link_context(self):
        self.ensure_one()
        if self._get_calculator_template():
            return {
                "isLinkable": True,
                "writable": False,
                "model": "sale.order",
                "resId": False,
                "recordName": False,
            }
        return super()._get_link_context()
