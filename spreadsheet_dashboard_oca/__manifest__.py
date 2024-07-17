# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Spreadsheet Dashboard Oca",
    "summary": """
        Use OCA Spreadsheets on dashboards configuration""",
    "version": "16.0.1.2.0",
    "license": "AGPL-3",
    "author": "CreuBlanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/spreadsheet",
    "depends": [
        "spreadsheet_dashboard",
        "spreadsheet_oca",
        "base_view_inheritance_extension",
    ],
    "data": [
        "wizards/spreadsheet_spreadsheet_import.xml",
        "views/spreadsheet_dashboard_group_views.xml",
        "views/spreadsheet_dashboard.xml",
        "data/spreadsheet_spreadsheet_import_mode.xml",
    ],
}
