import * as spreadsheet from "@odoo/o-spreadsheet";

import {Component, onWillStart, useProps} from "@odoo/owl";
import {Domain} from "@web/core/domain";
import {SpreadsheetControlPanel} from "./spreadsheet_controlpanel.esm";
import {SpreadsheetRenderer} from "./spreadsheet_renderer.esm";
import {deepCopy} from "@web/core/utils/objects";
import {helpers} from "@odoo/o-spreadsheet";
import {registry} from "@web/core/registry";
import {standardActionServiceProps} from "@web/webclient/actions/action_plugin";
import {useService} from "@web/core/utils/hooks";
import {useSubEnv} from "@web/owl2/utils";

const {load} = spreadsheet;

const {UuidGenerator} = spreadsheet.helpers;
const actionRegistry = registry.category("actions");
const {parseDimension, isDateOrDatetimeField} = helpers;

function normalizeGroupBys(dimensions, fields) {
    return dimensions.map((dimension) => {
        if (
            isDateOrDatetimeField(fields[dimension.fieldName]) &&
            !dimension.granularity
        ) {
            return {granularity: "month", ...dimension};
        }
        return dimension;
    });
}

export class ActionSpreadsheetOca extends Component {
    static template = "spreadsheet_oca.ActionSpreadsheetOca";
    static components = {
        SpreadsheetRenderer,
        SpreadsheetControlPanel,
    };
    props = useProps(standardActionServiceProps);

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        const params = this.props.action.params || this.props.action.context.params;
        this.spreadsheetId = params.spreadsheet_id || params.active_id;
        this.model = params.model || "spreadsheet.spreadsheet";
        this.import_data = params.import_data || {};
        onWillStart(async () => {
            // We need to load in case the data comes from an XLSX
            this.record =
                load(
                    await this.orm.call(
                        this.model,
                        "get_spreadsheet_data",
                        [[this.spreadsheetId]],
                        {context: {bin_size: false}}
                    )
                ) || {};
        });
        useSubEnv({
            saveRecord: this.saveRecord.bind(this),
            importData: this.importData.bind(this),
            notifyUser: this.notifyUser.bind(this),
        });
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
        if (this.import_data.new === undefined && this.import_data.new_sheet) {
            sheetId = UuidGenerator.smallUuid();
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
        const metaData = this.import_data.metaData;
        const chartType = metaData.mode;
        const chartId = UuidGenerator.smallUuid();
        const definition = {
            dataSource: {
                type: "odoo",
                metaData: {
                    groupBy: JSON.parse(JSON.stringify(metaData.groupBy)),
                    measure: metaData.measure,
                    order: metaData.order,
                    resModel: metaData.resModel,
                },
                searchParams: {
                    ...this.cleanSearchParams(),
                    domain: new Domain(this.import_data.searchParams.domain).toJson(),
                },
                actionXmlId: this.import_data.actionXmlId,
                cumulatedStart: metaData.cumulatedStart,
            },
            title: {text: this.import_data.name},
            type: chartType,
            fillArea: chartType === "line",
            background: "#FFFFFF",
            stacked: metaData.stacked,
            axisType: metaData.axisType,
            cumulative: metaData.cumulated || undefined,
            legendPosition: "top",
            verticalAxisPosition: "left",
            humanize: true,
            dataSetStyles: {},
            dataSourceId: UuidGenerator.smallUuid(),
            id: chartId,
        };
        spreadsheet_model.dispatch("CREATE_CHART", {
            sheetId,
            figureId: UuidGenerator.smallUuid(),
            chartId,
            col: 0,
            row: 0,
            offset: {x: 0, y: 0},
            definition,
        });
        spreadsheet_model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
            chartId,
            odooLink: {
                type: "dataSource",
                dataSourceCoreId: chartId,
                dataSourceType: "chart",
            },
        });
    }
    importCreateOrReuseSheet(spreadsheet_model) {
        var sheetId = spreadsheet_model.getters.getActiveSheetId();
        if (this.import_data.new === undefined) {
            sheetId = UuidGenerator.smallUuid();
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
        }
        return sheetId;
    }
    async importDataList(spreadsheet_model) {
        var sheetId = this.importCreateOrReuseSheet(spreadsheet_model);
        if (!sheetId) {
            const sheetIds = spreadsheet_model.getters.getSheetIds();
            sheetId = sheetIds.length ? sheetIds[0] : UuidGenerator.smallUuid();
        }
        const listId = spreadsheet_model.getters.getNextListId();
        const metaData = this.import_data.metaData;
        const columns = metaData.columns.map((c) => ({
            name: c.name,
            string: metaData.fields[c.name].string,
        }));
        const definition = {
            model: metaData.model,
            domain: new Domain(metaData.domain).toJson(),
            context: metaData.context,
            orderBy: metaData.orderBy,
            columns,
            name: this.import_data.name,
            actionXmlId: this.import_data.actionXmlId,
        };
        const linesNumber = this.import_data.dyn_number_of_rows || 80;
        spreadsheet_model.dispatch("INSERT_ODOO_LIST_WITH_TABLE", {
            sheetId,
            col: 0,
            row: 0,
            listId,
            definition,
            linesNumber,
            mode: "static",
        });
        const dataSource = spreadsheet_model.getters.getListDataSource(listId);
        await dataSource.load();
        spreadsheet_model.dispatch("AUTORESIZE_COLUMNS", {
            sheetId,
            cols: Array.from({length: columns.length}, (_, i) => i),
        });
    }
    async importDataPivot(spreadsheet_model) {
        var sheetId = this.importCreateOrReuseSheet(spreadsheet_model);
        const pivotId = UuidGenerator.smallUuid();
        const fields = this.import_data.metaData.fields || {};
        const activeMeasures = this.import_data.metaData.activeMeasures;
        const measures = activeMeasures.map((measure) => ({
            id: fields[measure]?.aggregator
                ? `${measure}:${fields[measure].aggregator}`
                : measure,
            fieldName: measure,
            aggregator: fields[measure]?.aggregator,
        }));
        const sortedMeasure = this.import_data.metaData.sortedColumn?.measure;
        const sortedColumn = activeMeasures.includes(sortedMeasure)
            ? this.import_data.metaData.sortedColumn
            : null;
        const colGroupBys = (this.import_data.metaData.colGroupBys || []).concat(
            this.import_data.metaData.expandedColGroupBys || []
        );
        const rowGroupBys = (this.import_data.metaData.rowGroupBys || []).concat(
            this.import_data.metaData.expandedRowGroupBys || []
        );
        const pivot_info = deepCopy({
            type: "ODOO",
            domain: new Domain(this.import_data.searchParams.domain).toJson(),
            context: this.import_data.searchParams.context,
            sortedColumn,
            measures,
            model: this.import_data.metaData.resModel,
            columns: normalizeGroupBys(colGroupBys.map(parseDimension), fields),
            rows: normalizeGroupBys(rowGroupBys.map(parseDimension), fields),
            name: this.import_data.name,
            actionXmlId: this.import_data.actionXmlId,
        });
        spreadsheet_model.dispatch("ADD_PIVOT", {
            pivotId,
            pivot: pivot_info,
        });
        const ds = spreadsheet_model.getters.getPivot(pivotId);
        await ds.load();
        const table = ds.getCollapsedTableStructure();
        spreadsheet_model.dispatch("INSERT_PIVOT_WITH_TABLE", {
            sheetId,
            col: 0,
            row: 0,
            pivotId,
            table: table.export(),
            pivotMode: "dynamic",
        });
        const columns = [];
        for (
            let col = 0;
            col <= table.columns[table.columns.length - 1].length;
            col++
        ) {
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
actionRegistry.add("action_spreadsheet_oca", ActionSpreadsheetOca, {
    force: true,
});
