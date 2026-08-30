# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Spreadsheet Dashboard Oca",
    "summary": """
        Use OCA Spreadsheets on dashboards configuration and manage
        dashboard share links""",
    "version": "19.0.2.0.0",
    "license": "AGPL-3",
    "author": "CreuBlanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/spreadsheet",
    "depends": [
        "spreadsheet_dashboard",
        "spreadsheet_oca",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "wizards/spreadsheet_spreadsheet_import.xml",
        "wizards/spreadsheet_to_dashboard.xml",
        "views/spreadsheet_dashboard_group_views.xml",
        "views/spreadsheet_dashboard.xml",
        "data/spreadsheet_spreadsheet_import_mode.xml",
    ],
    "assets": {
        "spreadsheet.o_spreadsheet": [
            (
                "after",
                "spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js",
                "spreadsheet_dashboard_oca/static/src/bundle/**/*.js",
            ),
            "spreadsheet_dashboard_oca/static/src/bundle/**/*.xml",
        ],
        "web.assets_unit_tests": [
            "spreadsheet_dashboard_oca/static/tests/**/*",
        ],
    },
}
