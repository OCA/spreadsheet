# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Spreadsheet Dashboard Oca",
    "summary": """
        Use OCA Spreadsheets on dashboards configuration""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "CreuBlanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/spreadsheet",
    "depends": [
        "spreadsheet_dashboard",
        "spreadsheet_oca",
    ],
    "data": [
        "views/spreadsheet_dashboard.xml",
    ],
}
