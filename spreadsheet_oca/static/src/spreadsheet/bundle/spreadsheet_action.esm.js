/** @odoo-module **/

import ListDataSource from "@spreadsheet/list/list_data_source";
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

    async importDataGraph(spreadsheet_model) {
        var sheetId = spreadsheet_model.getters.getActiveSheetId();
        var y = 0;
        if (this.import_data.new === undefined && this.import_data.new_sheet) {
            sheetId = uuidGenerator.uuidv4();
            spreadsheet_model.dispatch("CREATE_SHEET", {
                sheetId,
                position: spreadsheet_model.getters.getSheetIds().length,
            });
            // We want to open the new sheet
            const sheetIdFrom = spreadsheet_model.getters.getActiveSheetId();
            spreadsheet_model.dispatch("ACTIVATE_SHEET", {
                sheetIdFrom,
                sheetIdTo: sheetId,
            });
        } else if (this.import_data.new === undefined) {
            // TODO: Add a way to detect the last row total height
        }
        const dataSourceId = uuidGenerator.uuidv4();
        const definition = {
            title: this.import_data.metaData.title,
            type: "odoo_" + this.import_data.metaData.mode,
            background: "#FFFFFF",
            stacked: this.import_data.metaData.stacked,
            metaData: this.import_data.metaData,
            searchParams: this.import_data.searchParams,
            dataSourceId: dataSourceId,
            legendPosition: "top",
            verticalAxisPosition: "left",
        };
        spreadsheet_model.dispatch("CREATE_CHART", {
            sheetId,
            id: dataSourceId,
            position: {
                x: 0,
                y: y,
            },
            definition,
        });
    }
    importCreateOrReuseSheet(spreadsheet_model) {
        var sheetId = spreadsheet_model.getters.getActiveSheetId();
        var row = 0;
        if (this.import_data.new === undefined && this.import_data.new_sheet) {
            sheetId = uuidGenerator.uuidv4();
            spreadsheet_model.dispatch("CREATE_SHEET", {
                sheetId,
                position: spreadsheet_model.getters.getSheetIds().length,
            });
            // We want to open the new sheet
            const sheetIdFrom = spreadsheet_model.getters.getActiveSheetId();
            spreadsheet_model.dispatch("ACTIVATE_SHEET", {
                sheetIdFrom,
                sheetIdTo: sheetId,
            });
        } else if (this.import_data.new === undefined) {
            row = spreadsheet_model.getters.getNumberRows(sheetId);
            var maxcols = spreadsheet_model.getters.getNumberCols(sheetId);
            var filled = false;
            while (row >= 0) {
                for (var col = maxcols; col >= 0; col--) {
                    if (
                        spreadsheet_model.getters.getCell(sheetId, col, row) !==
                            undefined &&
                        !spreadsheet_model.getters.getCell(sheetId, col, row).isEmpty()
                    ) {
                        filled = true;
                        break;
                    }
                }
                if (filled) {
                    break;
                }
                row -= 1;
            }
            row += 1;
        }
        return {sheetId, row};
    }
    async importDataList(spreadsheet_model) {
        var {sheetId, row} = this.importCreateOrReuseSheet(spreadsheet_model);
        const dataSourceId = uuidGenerator.uuidv4();
        var list_info = {
            metaData: {
                resModel: this.import_data.metaData.model,
                columns: this.import_data.metaData.columns.map((column) => column.name),
                fields: this.import_data.metaData.fields,
            },
            searchParams: {
                domain: this.import_data.metaData.domain,
                context: this.import_data.metaData.context,
                orderBy: this.import_data.metaData.orderBy,
            },
            name: this.import_data.metaData.name,
        };
        const dataSource = spreadsheet_model.config.dataSources.add(
            dataSourceId,
            ListDataSource,
            list_info
        );
        await dataSource.load();
        spreadsheet_model.dispatch("INSERT_ODOO_LIST", {
            sheetId,
            col: 0,
            row: row,
            id: spreadsheet_model.getters.getNextListId(),
            dataSourceId,
            definition: list_info,
            linesNumber: this.import_data.metaData.threshold,
            columns: this.import_data.metaData.columns,
        });
        const columns = [];
        for (let col = 0; col < this.import_data.metaData.columns.length; col++) {
            columns.push(col);
        }
        spreadsheet_model.dispatch("AUTORESIZE_COLUMNS", {sheetId, cols: columns});
    }
    async importDataPivot(spreadsheet_model) {
        var {sheetId, row} = this.importCreateOrReuseSheet(spreadsheet_model);
        const dataSourceId = uuidGenerator.uuidv4();
        const colGroupBys = this.import_data.metaData.colGroupBys.concat(
            this.import_data.metaData.expandedColGroupBys
        );
        const rowGroupBys = this.import_data.metaData.rowGroupBys.concat(
            this.import_data.metaData.expandedRowGroupBys
        );
        const pivot_info = {
            metaData: {
                colGroupBys,
                rowGroupBys,
                activeMeasures: this.import_data.metaData.activeMeasures,
                resModel: this.import_data.metaData.resModel,
                sortedColumn: this.import_data.metaData.sortedColumn,
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
            row: row,
            id: spreadsheet_model.getters.getNextPivotId(),
            table,
            dataSourceId,
            definition: pivot_info,
        });
        const columns = [];
        for (let col = 0; col < table.cols[table.cols.length - 1].length; col++) {
            columns.push(col);
        }
        spreadsheet_model.dispatch("AUTORESIZE_COLUMNS", {sheetId, cols: columns});
    }
    async importData(spreadsheet_model) {
        if (this.import_data.mode === "pivot") {
            await this.importDataPivot(spreadsheet_model);
        }
        if (this.import_data.mode === "graph") {
            await this.importDataGraph(spreadsheet_model);
        }
        if (this.import_data.mode === "list") {
            await this.importDataList(spreadsheet_model);
        }
    }
}
ActionSpreadsheetOca.template = "spreadsheet_oca.ActionSpreadsheetOca";
ActionSpreadsheetOca.components = {
    SpreadsheetRenderer,
    SpreadsheetControlPanel,
};
actionRegistry.add("action_spreadsheet_oca", ActionSpreadsheetOca, {force: true});
