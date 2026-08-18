# Copyright 2026 arielbarreiros96
# License AGPL-3.0 or later (https://www.gnu.org/licenses/AGPL-3.0).
{
    "name": "Spreadsheet Field Linking",
    "version": "19.0.1.0.0",
    "summary": "Link spreadsheet cells to record fields and write their values back",
    "author": "arielbarreiros96, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/spreadsheet",
    "license": "AGPL-3",
    "category": "Productivity",
    "depends": ["spreadsheet_oca"],
    "data": [],
    "assets": {
        "spreadsheet.o_spreadsheet": [
            "spreadsheet_field_linking/static/src/field_linking/**/*.js",
            "spreadsheet_field_linking/static/src/field_linking/**/*.xml",
        ],
        "web.assets_unit_tests": [
            "spreadsheet_field_linking/static/tests/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
