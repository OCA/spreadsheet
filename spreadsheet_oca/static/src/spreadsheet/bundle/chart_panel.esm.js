import * as spreadsheet from "@odoo/o-spreadsheet";
import {patch} from "@web/core/utils/patch";

const {chartSubtypeRegistry} = spreadsheet.registries;
const {ChartTypePicker} = spreadsheet.components;

const ODOO_PREFIX = "odoo_";
const isOdooKey = (key) => key?.startsWith(ODOO_PREFIX);
// The only Odoo chart families this module knows how to create, convert
// between, and configure (see odoo_panels.esm.js). Core registers several
// other odoo_* chart types (combo, waterfall, sunburst, ...) that this
// module was never built to handle, so they're deliberately excluded.
const SUPPORTED_ODOO_CHART_TYPES = ["odoo_bar", "odoo_line", "odoo_pie"];

patch(ChartTypePicker.prototype, {
    setup() {
        super.setup();
        const definition = this.env.model.getters.getChartDefinition(
            this.props.chartId
        );
        const isOdoo = isOdooKey(definition.type);
        const filtered = {};
        for (const [category, items] of Object.entries(this.chartTypeByCategories)) {
            const matching = isOdoo
                ? items.filter((item) =>
                      SUPPORTED_ODOO_CHART_TYPES.includes(item.chartType)
                  )
                : items.filter((item) => !isOdooKey(item.chartType));
            if (matching.length) {
                filtered[category] = matching;
            }
        }
        this.chartTypeByCategories = filtered;
    },
    onTypeChange(type) {
        const {env} = this;
        const chartId = this.props.chartId;
        const current = env.model.getters.getChartDefinition(chartId);
        if (!isOdooKey(current.type)) {
            return super.onTypeChange(type);
        }
        // The store's default changeChartType always calls
        // ChartClass.getChartDefinitionFromContextCreation, which every Odoo
        // chart class inherits unconditionally-throwing from OdooChart, since
        // Odoo charts have no cell-range creation context to convert from.
        // Bypass the store and dispatch UPDATE_CHART directly instead.
        const newChartInfo = chartSubtypeRegistry.get(type);
        const definition = {
            ...current,
            ...newChartInfo.subtypeDefinition,
            type: newChartInfo.chartType,
        };
        const figureId = env.model.getters.getFigureIdFromChartId(chartId);
        const sheetId = env.model.getters.getFigureSheetId(figureId);
        env.model.dispatch("UPDATE_CHART", {
            definition,
            chartId,
            figureId,
            sheetId,
        });
        this.closePopover();
    },
});
