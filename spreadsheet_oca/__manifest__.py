# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Spreadsheet Oca",
    "summary": """
        Allow to edit spreadsheets""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "CreuBlanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/spreadsheet",
    "depends": ["spreadsheet", "base_sparse_field"],
    "data": [
        "security/ir.model.access.csv",
        "views/spreadsheet_spreadsheet.xml",
    ],
    "assets": {
        "web.assets_backend": [
            ("include", "spreadsheet.o_spreadsheet"),
            "spreadsheet/static/src/assets_backend/**/*",
            "spreadsheet_oca/static/src/spreadsheet/spreadsheet.xml",
            "spreadsheet_oca/static/src/spreadsheet/spreadsheet_view.esm.js",
        ],
    },
}
