# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Spreadsheet Quotation Calculator",
    "summary": (
        "Use spreadsheets as quotation calculators linked " "to sale order templates"
    ),
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Odoo Community Association (OCA), Cloud Lotus",
    "website": "https://github.com/OCA/spreadsheet",
    "depends": ["spreadsheet_oca", "sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/spreadsheet_quotation_create.xml",
        "views/sale_order_template_views.xml",
        "views/sale_order_views.xml",
    ],
    "assets": {
        "spreadsheet.o_spreadsheet": [
            "spreadsheet_quotation/static/src/quotation_spreadsheet/field_sync_plugin.esm.js",
            "spreadsheet_quotation/static/src/quotation_spreadsheet/field_sync_side_panel.esm.js",
            "spreadsheet_quotation/static/src/quotation_spreadsheet/field_sync_side_panel.xml",
            "spreadsheet_quotation/static/src/quotation_spreadsheet/quotation_spreadsheet.xml",
        ],
    },
    "installable": True,
    "development_status": "Alpha",
}
