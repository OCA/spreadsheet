/** @odoo-module **/
import {ListController} from "@web/views/list/list_controller";

import {patch} from "web.utils";

patch(
    ListController.prototype,
    "spreadsheet_oca/static/src/spreadsheet/list_controller.esm.js",
    {
        onSpreadsheetButtonClicked() {
            this.env.bus.trigger("addListOnSpreadsheet");
        },
    }
);
