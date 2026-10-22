# Copyright 2026 arielbarreiros96
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0).
{
    "name": "Spreadsheet Sale Calculator",
    "version": "19.0.3.0.0",
    "summary": "Drive sale order line values from an embedded Odoo spreadsheet",
    "author": "arielbarreiros96, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/spreadsheet",
    "license": "AGPL-3",
    "category": "Sales",
    "depends": ["sale_management", "spreadsheet_field_linking"],
    "data": [
        "security/spreadsheet_sale_calculator_groups.xml",
        "views/sale_order_template_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
