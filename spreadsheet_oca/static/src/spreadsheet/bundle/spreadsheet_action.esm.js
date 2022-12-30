/** @odoo-module **/

import {SpreadsheetControlPanel} from "./spreadsheet_controlpanel.esm";
import {SpreadsheetRenderer} from "./spreadsheet_renderer.esm";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

const actionRegistry = registry.category("actions");

const {Component, onMounted, onWillStart, useSubEnv} = owl;

export class ActionSpreadsheetOca extends Component {
    setup() {
        this.router = useService("router");
        this.orm = useService("orm");
        const params = this.props.action.params || this.props.action.context.params;
        this.spreadsheetId = params.spreadsheet_id;
        this.model = params.model || "spreadsheet.spreadsheet";
        onMounted(() => {
            this.router.pushState({
                spreadsheet_id: this.spreadsheetId,
                model: this.model,
            });
        });
        onWillStart(async () => {
            var record = await this.orm.call(
                this.model,
                "read",
                [[this.spreadsheetId], ["name", "raw"]],
                {context: {bin_size: false}}
            );
            this.record = record[0];
        });
        useSubEnv({
            saveRecord: this.saveRecord.bind(this),
        });
    }
    saveRecord(data) {
        if (this.spreadsheetId) {
            this.orm.call(this.model, "write", [this.spreadsheetId, data]);
        } else {
            this.spreadsheetId = this.orm.call(this.model, "create", [data])[0];
            this.router.pushState({spreadsheet_id: this.spreadsheetId});
        }
    }
}
ActionSpreadsheetOca.template = "spreadsheet_oca.ActionSpreadsheetOca";
ActionSpreadsheetOca.components = {
    SpreadsheetRenderer,
    SpreadsheetControlPanel,
};
actionRegistry.add("action_spreadsheet_oca", ActionSpreadsheetOca, {force: true});
