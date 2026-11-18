# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Spreadsheet MIS Builder",
    "summary": "Use MIS Builder KPIs in spreadsheets",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "KMEE, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/spreadsheet",
    "category": "Accounting",
    "depends": ["spreadsheet_oca", "mis_builder"],
    "data": ["views/mis_report_instance.xml"],
    "demo": ["demo/account_move.xml", "demo/mis_report.xml"],
    "assets": {
        "spreadsheet.o_spreadsheet": [
            "spreadsheet_mis_builder/static/src/bundle/**/*.js",
        ],
        "web.assets_backend": [
            "spreadsheet_mis_builder/static/src/components/**/*",
        ],
    },
}
