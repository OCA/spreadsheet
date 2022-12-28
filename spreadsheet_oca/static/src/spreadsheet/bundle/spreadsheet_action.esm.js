/** @odoo-module **/

import PivotDataSource from "@spreadsheet/pivot/pivot_data_source";
import {SpreadsheetControlPanel} from "./spreadsheet_controlpanel.esm";
import {SpreadsheetRenderer} from "./spreadsheet_renderer.esm";
import {registry} from "@web/core/registry";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import {useService} from "@web/core/utils/hooks";

const uuidGenerator = new spreadsheet.helpers.UuidGenerator();
const actionRegistry = registry.category("actions");
const {Component, onMounted, onWillStart, useSubEnv} = owl;

export class ActionSpreadsheetOca extends Component {
    setup() {
        this.router = useService("router");
        this.orm = useService("orm");
        const params = this.props.action.params || this.props.action.context.params;
        this.spreadsheetId = params.spreadsheet_id;
        this.model = params.model || "spreadsheet.spreadsheet";
        this.import_data = params.import_data || {};
        onMounted(() => {
            this.router.pushState({
                spreadsheet_id: this.spreadsheetId,
                model: this.model,
            });
        });
        onWillStart(async () => {
            this.record =
                (await this.orm.call(
                    this.model,
                    "get_spreadsheet_data",
                    [[this.spreadsheetId]],
                    {context: {bin_size: false}}
                )) || {};
        });
        useSubEnv({
            saveRecord: this.saveRecord.bind(this),
            importData: this.importData.bind(this),
        });
    }
    async saveRecord(data) {
        if (this.record.mode === "readonly") {
            return;
        }
        if (this.spreadsheetId) {
            this.orm.call(this.model, "write", [this.spreadsheetId, data]);
        } else {
            this.spreadsheetId = await this.orm.call(this.model, "create", [data]);
            this.router.pushState({spreadsheet_id: this.spreadsheetId});
        }
    }
    async importDataPivot(spreadsheet_model) {
        const sheetId = spreadsheet_model.getters.getActiveSheetId();
        const dataSourceId = uuidGenerator.uuidv4();
        const pivot_info = {
            metaData: {
                colGroupBys: this.import_data.metaData.colGroupBys,
                rowGroupBys: this.import_data.metaData.rowGroupBys,
                activeMeasures: this.import_data.metaData.activeMeasures,
                resModel: this.import_data.metaData.resModel,
            },
            searchParams: this.import_data.searchParams,
        };
        const dataSource = spreadsheet_model.config.dataSources.add(
            dataSourceId,
            PivotDataSource,
            pivot_info
        );
        await dataSource.load();
        const {cols, rows, measures} = dataSource.getTableStructure().export();
        const table = {
            cols,
            rows,
            measures,
        };
        spreadsheet_model.dispatch("INSERT_PIVOT", {
            sheetId,
            col: 0,
            row: 0,
            id: spreadsheet_model.getters.getNextPivotId(),
            table,
            dataSourceId,
            definition: pivot_info,
        });
    }
    async importData(spreadsheet_model) {
        if (this.import_data.mode === "pivot") {
            await this.importDataPivot(spreadsheet_model);
        }
    }
}
ActionSpreadsheetOca.template = "spreadsheet_oca.ActionSpreadsheetOca";
ActionSpreadsheetOca.components = {
    SpreadsheetRenderer,
    SpreadsheetControlPanel,
};
actionRegistry.add("action_spreadsheet_oca", ActionSpreadsheetOca, {force: true});
