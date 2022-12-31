/** @odoo-module **/

import {ListController} from "@web/views/list/list_controller";
import {listView} from "@web/views/list/list_view";
import {registry} from "@web/core/registry";

export class SpreadsheetListController extends ListController {
    async createRecord() {
        this.actionService.doAction({
            target: "current",
            tag: "action_spreadsheet_oca",
            type: "ir.actions.client",
            params: {
                model: this.props.resModel,
            },
        });
    }
    async openRecord(record) {
        this.actionService.doAction({
            target: "current",
            tag: "action_spreadsheet_oca",
            type: "ir.actions.client",
            params: {
                model: this.props.resModel,
                spreadsheet_id: record.resId,
            },
        });
    }
}

export const spreadsheetListView = {
    ...listView,
    Controller: SpreadsheetListController,
};

registry.category("views").add("spreadsheet_list", spreadsheetListView);
