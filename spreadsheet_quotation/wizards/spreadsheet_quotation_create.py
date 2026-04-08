# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import uuid

from odoo import _, api, fields, models

DEFAULT_COLUMNS = [
    "product_id",
    "product_uom_qty",
    "qty_delivered",
    "qty_invoiced",
    "qty_to_invoice",
    "product_uom_id",
    "price_unit",
    "price_tax",
    "price_subtotal",
]

DEFAULT_LINE_COUNT = 20


class SpreadsheetQuotationCreate(models.TransientModel):
    _name = "spreadsheet.quotation.create"
    _description = "Create Quotation Calculator Spreadsheet"

    sale_order_template_id = fields.Many2one(
        "sale.order.template",
        required=True,
        readonly=True,
    )
    name = fields.Char(
        default="Quotation Calculator",
        required=True,
    )
    line_count = fields.Integer(
        string="Number of lines",
        default=DEFAULT_LINE_COUNT,
        help="Initial number of rows to display in the list.",
    )

    def action_create(self):
        self.ensure_one()
        spreadsheet_data = self._build_spreadsheet_data()
        spreadsheet = self.env["spreadsheet.spreadsheet"].create(
            {
                "name": self.name,
                "spreadsheet_raw": spreadsheet_data,
            }
        )
        self.sale_order_template_id.spreadsheet_id = spreadsheet
        return spreadsheet.open_spreadsheet()

    def _build_spreadsheet_data(self):
        columns = DEFAULT_COLUMNS
        line_count = self.line_count or DEFAULT_LINE_COUNT
        filter_id = str(uuid.uuid4())
        list_id = "1"
        sheet_id = "sheet1"

        cells = self._build_cells(list_id, columns, line_count)
        col_count = len(columns)

        lang = self.env["res.lang"]._lang_get(self.env.user.lang)
        locale = lang._odoo_lang_to_spreadsheet_locale()

        return {
            "version": 1,
            "sheets": [
                {
                    "id": sheet_id,
                    "name": _("Sale Order Lines"),
                    "cells": cells,
                    "colNumber": max(col_count, 10),
                    "rowNumber": max(line_count + 2, 30),
                }
            ],
            "settings": {"locale": locale},
            "revisionId": "START_REVISION",
            "lists": {
                list_id: {
                    "columns": columns,
                    "domain": [["display_type", "=", False]],
                    "model": "sale.order.line",
                    "context": {},
                    "orderBy": [],
                    "id": list_id,
                    "name": _("Sale Order Lines"),
                    "fieldMatching": {
                        filter_id: {
                            "chain": "order_id",
                            "type": "many2one",
                        }
                    },
                }
            },
            "listNextId": 2,
            "globalFilters": [
                {
                    "id": filter_id,
                    "type": "relation",
                    "label": _("Sale Order"),
                    "modelName": "sale.order",
                    "defaultValue": [],
                }
            ],
        }

    @api.model
    def _build_cells(self, list_id, columns, line_count):
        cells = {}
        for col_idx, col_name in enumerate(columns):
            col_letter = self._col_index_to_letter(col_idx)
            cells[f"{col_letter}1"] = {
                "content": f'=ODOO.LIST.HEADER({list_id},"{col_name}")',
            }
            for row in range(1, line_count + 1):
                cells[f"{col_letter}{row + 1}"] = {
                    "content": f'=ODOO.LIST({list_id},{row},"{col_name}")',
                }
        return cells

    @api.model
    def _col_index_to_letter(self, idx):
        """Convert a 0-based column index to spreadsheet letters.

        Examples: A, B, ..., Z, AA, ...
        """
        result = ""
        while True:
            result = chr(ord("A") + idx % 26) + result
            idx = idx // 26 - 1
            if idx < 0:
                break
        return result
