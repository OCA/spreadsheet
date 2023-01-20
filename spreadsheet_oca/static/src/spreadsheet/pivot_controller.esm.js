/** @odoo-module **/
import {PivotController} from "@web/views/pivot/pivot_controller";

import {patch} from "web.utils";

patch(
    PivotController.prototype,
    "spreadsheet_oca/static/src/spreadsheet/pivot_controller.esm.js",
    {
        onSpreadsheetButtonClicked() {
            this.actionService.doAction(
                "spreadsheet_oca.spreadsheet_spreadsheet_import_act_window",
                {
                    additionalContext: {
                        default_name: this.model.metaData.title,
                        default_import_data: {
                            mode: "pivot",
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
