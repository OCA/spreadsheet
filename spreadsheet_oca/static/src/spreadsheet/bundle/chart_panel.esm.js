import * as spreadsheet from "@odoo/o-spreadsheet";
import {patch} from "@web/core/utils/patch";
import {onWillUpdateProps} from "@odoo/owl";

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
        if (!chartId) {
            return super.onTypeChange(type);
        }
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
        env.model.dispatch("UPDATE_CHART", {
            definition,
            id: chartId,
            sheetId: env.model.getters.getActiveSheetId(),
        });
        this.closePopover();
    },
    filterCategoriesChartType(chartId) {
        if (!chartId) {
            return;
        }
        const {env} = this;
        const definition = getChartDefinition(env, chartId);
        const isOdoo = isOdooKey(definition.type);
        const registryItems = chartSubtypeRegistry
            .getAll()
            .filter((item) => isOdoo === isOdooKey(item.chartType));
        this.chartTypeByCategories = groupByCategory(registryItems);
    },
});
