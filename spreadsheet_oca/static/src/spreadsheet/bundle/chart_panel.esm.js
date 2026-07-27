import * as spreadsheet from "@odoo/o-spreadsheet";
import {onWillUpdateProps} from "@odoo/owl";
import {patch} from "@web/core/utils/patch";

const {chartSubtypeRegistry} = spreadsheet.registries;
const {ChartTypePicker} = spreadsheet.components;

const ODOO_PREFIX = "odoo_";
const isOdooKey = (key) => key?.startsWith(ODOO_PREFIX);

const groupByCategory = (items) =>
    items.reduce((acc, item) => {
        (acc[item.category] ||= []).push(item);
        return acc;
    }, {});

const getChartDefinition = (env, chartId) =>
    env.model.getters.getChartDefinition(chartId);

patch(ChartTypePicker.prototype, {
    setup() {
        super.setup();
        const refresh = (chartId) => this.filterCategoriesChartType(chartId);
        refresh(this.props.chartId);
        onWillUpdateProps((nextProps) => refresh(nextProps.chartId));
    },

    getChartTypes(isOdoo) {
        const result = {};
        for (const key of chartSubtypeRegistry.getKeys()) {
            if (isOdoo === isOdooKey(key)) {
                result[key] = chartSubtypeRegistry.get(key).name;
            }
        }
        return result;
    },
    onTypeChange(type) {
        const {env} = this;
        const chartId = this.props.chartId;
        const current = getChartDefinition(env, chartId);
        if (!isOdooKey(current.type)) {
            return super.onTypeChange(type);
        }
        const newChartInfo = chartSubtypeRegistry.get(type);
        const definition = {
            verticalAxisPosition: "left",
            ...current,
            ...newChartInfo.subtypeDefinition,
            type: newChartInfo.chartType,
        };
        const figureId = env.model.getters.getFigureIdFromChartId(chartId);
        env.model.dispatch("UPDATE_CHART", {
            definition,
            chartId,
            figureId,
            sheetId: env.model.getters.getFigureSheetId(figureId),
        });
        this.closePopover();
    },
    filterCategoriesChartType(chartId) {
        const {env} = this;
        const definition = getChartDefinition(env, chartId);
        const isOdoo = isOdooKey(definition.type);
        const registryItems = chartSubtypeRegistry
            .getAll()
            .filter((item) => isOdoo === isOdooKey(item.chartType));
        this.chartTypeByCategories = groupByCategory(registryItems);
    },
});
