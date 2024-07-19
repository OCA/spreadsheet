/** @odoo-module **/
import {GraphController} from "@web/views/graph/graph_controller";

import {patch} from "web.utils";

patch(
    GraphController.prototype,
    "spreadsheet_oca/static/src/spreadsheet/graph_controller.esm.js",
    {
        onSpreadsheetButtonClicked() {
            this.actionService.doAction(
                "spreadsheet_oca.spreadsheet_spreadsheet_import_act_window",
                {
                    additionalContext: {
                        default_name: this.model.metaData.title,
                        default_datasource_name: this.model.metaData.title,
                        default_import_data: {
                            mode: "graph",
                            metaData: JSON.parse(JSON.stringify(this.model.metaData)),
                            searchParams: JSON.parse(
                                JSON.stringify(this.model.searchParams)
                            ),
                        },
                    },
                }
            );
        },
    }
);
