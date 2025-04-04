# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Spreadsheet Oca",
    "summary": """
        Allow to edit spreadsheets""",
    "version": "17.0.1.0.0",
    "license": "AGPL-3",
    "author": "CreuBlanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/spreadsheet",
    "depends": ["spreadsheet", "base_sparse_field", "bus"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/spreadsheet_spreadsheet.xml",
        "data/spreadsheet_spreadsheet_import_mode.xml",
        "wizards/spreadsheet_select_row_number.xml",
        "wizards/spreadsheet_spreadsheet_import.xml",
    ],
    "demo": ["demo/spreadsheet_spreadsheet.xml"],
    "assets": {
        "web.assets_backend": [
            "spreadsheet_oca/static/src/spreadsheet_tree/spreadsheet_tree_view.esm.js",
            "spreadsheet_oca/static/src/spreadsheet_tree/spreadsheet_tree_view.xml",
            "spreadsheet_oca/static/src/spreadsheet/spreadsheet.scss",
            "spreadsheet_oca/static/src/spreadsheet/spreadsheet_action.esm.js",
            "spreadsheet_oca/static/src/spreadsheet/pivot_controller.esm.js",
            "spreadsheet_oca/static/src/spreadsheet/graph_controller.esm.js",
            "spreadsheet_oca/static/src/spreadsheet/list_controller.esm.js",
            "spreadsheet_oca/static/src/spreadsheet/list_renderer.esm.js",
            (
                "after",
                "web/static/src/views/graph/graph_controller.xml",
                "spreadsheet_oca/static/src/spreadsheet/graph_controller.xml",
            ),
            (
                "after",
                "web/static/src/views/list/list_controller.xml",
                "spreadsheet_oca/static/src/spreadsheet/list_controller.xml",
            ),
            (
                "after",
                "web/static/src/views/pivot/pivot_controller.xml",
                "spreadsheet_oca/static/src/spreadsheet/pivot_controller.xml",
            ),
        ],
        "spreadsheet.o_spreadsheet": [
            "spreadsheet_oca/static/src/spreadsheet/bundle/spreadsheet.xml",
            "spreadsheet_oca/static/src/spreadsheet/bundle/filter.esm.js",
            "spreadsheet_oca/static/src/spreadsheet/bundle/filter_panel_datasources.esm.js",
            "spreadsheet_oca/static/src/spreadsheet/bundle/spreadsheet_renderer.esm.js",
            "spreadsheet_oca/static/src/spreadsheet/bundle/spreadsheet_controlpanel.esm.js",
            "spreadsheet_oca/static/src/spreadsheet/bundle/spreadsheet_action.esm.js",
            "spreadsheet_oca/static/src/spreadsheet/bundle/odoo_panels.esm.js",
            "spreadsheet_oca/static/src/spreadsheet/bundle/chart_panels.esm.js",
            "spreadsheet_oca/static/src/spreadsheet/bundle/chart_panel.esm.js",
            "spreadsheet_oca/static/src/spreadsheet/utils/dynamic_generators.esm.js",
            "spreadsheet_oca/static/src/pivot/pivot_table.esm.js",
        ],
    },
}
