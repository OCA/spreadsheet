/** @odoo-module **/

import {Component} from "@odoo/owl";
import {DataSources} from "@spreadsheet/data_sources/data_sources";
import {Field} from "@web/views/fields/field";
import {loadSpreadsheetDependencies} from "@spreadsheet/helpers/helpers";
import {migrate} from "@spreadsheet/o_spreadsheet/migration";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

import {useService} from "@web/core/utils/hooks";

const {Spreadsheet, Model} = spreadsheet;
const {useSubEnv, onWillStart} = owl;

export class SpreadsheetRenderer extends Component {
    setup() {
        this.orm = useService("orm");
        const dataSources = new DataSources(this.orm);
        this.spreadsheet_model = new Model(migrate(JSON.parse(this.props.record.raw)), {
            evalContext: {env: this.env, orm: this.orm},
            dataSources,
        });
        useSubEnv({
            saveSpreadsheet: this.onSpreadsheetSaved.bind(this),
        });
        onWillStart(async () => {
            await loadSpreadsheetDependencies();
            await dataSources.waitForAllLoaded();
            // Await waitForDataLoaded(this.spreadsheet_model);
        });
        dataSources.addEventListener("data-source-updated", () => {
            const sheetId = this.spreadsheet_model.getters.getActiveSheetId();
            this.spreadsheet_model.dispatch("EVALUATE_CELLS", {sheetId});
        });
    }
    onSpreadsheetSaved() {
        const data = this.spreadsheet_model.exportData();
        this.env.saveRecord({raw: JSON.stringify(data)});
    }
}

SpreadsheetRenderer.template = "spreadsheet_oca.SpreadsheetRenderer";
SpreadsheetRenderer.components = {
    Spreadsheet,
    Field,
};
SpreadsheetRenderer.props = {
    record: Object,
};
