import * as spreadsheet from "@odoo/o-spreadsheet";
import {makeDynamicCols, makeDynamicRows} from "../utils/dynamic_generators.esm";
import {SpreadsheetControlPanel} from "./spreadsheet_controlpanel.esm";
import {SpreadsheetRenderer} from "./spreadsheet_renderer.esm";
import {registry} from "@web/core/registry";
import {standardActionServiceProps} from "@web/webclient/actions/action_service";
import {useService} from "@web/core/utils/hooks";
import {useSetupAction} from "@web/search/action_hook";

const {load} = spreadsheet;

const uuidGenerator = new spreadsheet.helpers.UuidGenerator();
const actionRegistry = registry.category("actions");
const {Component, onWillStart, useSubEnv, useState} = owl;

export class ActionSpreadsheetOca extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        if (this.props.state && this.props.state.spreadsheetId) {
            this.spreadsheetId = this.props.state.spreadsheetId;
            this.model = this.props.state.model || "spreadsheet.spreadsheet";
            this.import_data = {};
        } else {
            let params = {};

            if (this.props.action.params) {
                params = this.props.action.params;
            }

            if (this.props.action.context) {
                // On page refresh, the active_id might be in context
                const context = this.props.action.context;
                params = {...params, ...context};

                if (context.active_id && !params.spreadsheet_id) {
                    params.spreadsheet_id = context.active_id;
                }
            }

            if (this.props.action.additionalContext) {
                params = {...params, ...this.props.action.additionalContext};
            }

            this.spreadsheetId =
                params.spreadsheet_id || params.resId || params.id || params.active_id;
            this.model = params.model || "spreadsheet.spreadsheet";
            this.import_data = params.import_data || {};
        }

        this.state = useState({
            record: {
                name: "",
                mode: "normal",
                spreadsheet_raw: {},
            },
        });

        useSetupAction({
            getLocalState: () => {
                return {
                    spreadsheetId: this.spreadsheetId,
                    model: this.model,
                    recordName: this.state.record.name,
                    recordMode: this.state.record.mode,
                };
            },
        });

        onWillStart(async () => {
            if (!this.spreadsheetId) {
                return;
            }

            const data = await this.orm.call(
                this.model,
                "get_spreadsheet_data",
                [[this.spreadsheetId]],
                {context: {bin_size: false}}
            );
            // The load function processes the spreadsheet_raw data but may not preserve other fields
            // So we need to merge the loaded data with the original data to keep the name
            const loadedData = load(data) || {};
            this.state.record = {
                ...loadedData,
                name: data.name || "", // Preserve the name from the original data
                mode: data.mode || "normal",
            };
            // Keep a non-reactive reference for backward compatibility
            this.record = this.state.record;
        });
        useSubEnv({
            saveRecord: this.saveRecord.bind(this),
            importData: this.importData.bind(this),
            notifyUser: this.notifyUser.bind(this),
        });
    }

    get record() {
        return this.state.record;
    }

    set record(value) {
        this.state.record = value;
    }

    notifyUser(notification) {
        this.notification.add(notification.text, {
            type: notification.type,
            sticky: notification.sticky,
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
        }
    }
    /**
     * Clean SearchParams of conflictive keys.
     *
     * 1. Removed from context pivot conflictive keys.
     * 2. Removed from context graph conflictive keys.
     *
     * @returns {Object}       Formated searchParams.
     */
    cleanSearchParams() {
        const searchParams = this.import_data.searchParams;
        const context = {};
        for (var key of Object.keys(searchParams.context)) {
            if (key.startsWith("pivot_") || key.startsWith("graph_")) {
                continue;
            }
            context[key] = searchParams.context[key];
        }
        return {...searchParams, context};
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
            title: this.import_data.name,
            type: "odoo_" + this.import_data.metaData.mode,
            background: "#FFFFFF",
            stacked: this.import_data.metaData.stacked,
            metaData: this.import_data.metaData,
            searchParams: this.cleanSearchParams(),
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
        const listId = spreadsheet_model.getters.getNextListId();

        // Build the definition with the correct structure
        const definition = {
            metaData: {
                resModel: this.import_data.metaData.model,
                columns: this.import_data.metaData.columns.map((column) =>
                    typeof column === "string" ? column : column.name
                ),
                fields: this.import_data.metaData.fields || {},
            },
            searchParams: {
                domain: this.import_data.metaData.domain || [],
                context: this.import_data.metaData.context || {},
                orderBy: this.import_data.metaData.orderBy || [],
            },
            name: this.import_data.name || this.import_data.datasource_name || "List",
        };

        spreadsheet_model.dispatch("INSERT_ODOO_LIST", {
            sheetId,
            col: 0,
            row: row,
            id: listId,
            definition: definition,
            linesNumber: this.import_data.dyn_number_of_rows || 10,
            columns: this.import_data.metaData.columns || [],
        });

        const columns = [];
        const columnCount = this.import_data.metaData.columns
            ? this.import_data.metaData.columns.length
            : 0;
        for (let col = 0; col < columnCount; col++) {
            columns.push(col);
        }
        if (columns.length > 0) {
            spreadsheet_model.dispatch("AUTORESIZE_COLUMNS", {
                sheetId,
                cols: columns,
            });
        }
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
        const pivotMeasures = this.import_data.metaData.activeMeasures.map(
            (measure) => {
                if (typeof measure === "string") {
                    // Convert string measure to object format
                    return {
                        id: measure,
                        fieldName: measure,
                        aggregator: measure === "__count" ? "count" : "sum",
                    };
                }
                return measure;
            }
        );

        const pivot_info = {
            type: "ODOO",
            model: this.import_data.metaData.resModel,
            domain: this.cleanSearchParams().domain || [],
            context: this.cleanSearchParams().context || {},
            measures: pivotMeasures,
            columns: colGroupBys.map((groupBy) => ({
                fieldName: groupBy.split(":")[0],
                granularity: groupBy.split(":")[1] || undefined,
            })),
            rows: rowGroupBys.map((groupBy) => ({
                fieldName: groupBy.split(":")[0],
                granularity: groupBy.split(":")[1] || undefined,
            })),
            sortedColumn: this.import_data.metaData.sortedColumn,
            name: this.import_data.name,
        };
        spreadsheet_model.dispatch("ADD_PIVOT", {
            pivotId: dataSourceId,
            pivot: pivot_info,
        });
        const dataSource = spreadsheet_model.getters.getPivot(dataSourceId);
        await dataSource.load();
        var tableStructure = dataSource.getTableStructure();
        var {cols, rows, measures} = tableStructure.export
            ? tableStructure.export()
            : tableStructure;
        if (this.import_data.dyn_number_of_rows) {
            const indentations = rows.map((r) => r.indent || 0);
            const max_indentation =
                indentations.length > 0 ? Math.max(...indentations) : 0;
            rows = makeDynamicRows(
                rowGroupBys,
                this.import_data.dyn_number_of_rows,
                1,
                max_indentation
            );
        }
        if (this.import_data.dyn_number_of_cols) {
            cols = makeDynamicCols(
                colGroupBys,
                this.import_data.dyn_number_of_cols,
                measures || this.import_data.metaData.activeMeasures
            );
        }
        const table = {
            cols,
            rows,
            measures,
        };
        spreadsheet_model.dispatch("INSERT_PIVOT", {
            sheetId,
            col: 0,
            row: row,
            pivotId: dataSourceId,
            table,
        });
        const columns = [];
        if (table.cols && table.cols.length > 0 && table.cols[table.cols.length - 1]) {
            for (let col = 0; col < table.cols[table.cols.length - 1].length; col++) {
                columns.push(col);
            }
        }
        spreadsheet_model.dispatch("AUTORESIZE_COLUMNS", {
            sheetId,
            cols: columns,
        });
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
ActionSpreadsheetOca.props = {...standardActionServiceProps};
actionRegistry.add("action_spreadsheet_oca", ActionSpreadsheetOca, {
    force: true,
});
