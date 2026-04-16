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

const getFigureDefinition = (env, figureId) =>
    env.model.getters.getChartDefinition(figureId);

patch(ChartTypePicker.prototype, {
    setup() {
        super.setup();
        const refresh = (figureId) => this.filterCategoriesChartType(figureId);
        refresh(this.props.figureId);
        onWillUpdateProps((nextProps) => refresh(nextProps.figureId));
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
        const figureId = this.props.figureId;
        const current = getFigureDefinition(env, figureId);
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
            id: figureId,
            sheetId: env.model.getters.getActiveSheetId(),
        });
        this.closePopover();
    },
    filterCategoriesChartType(figureId) {
        const {env} = this;
        const definition = getFigureDefinition(env, figureId);
        const isOdoo = isOdooKey(definition.type);
        const registryItems = chartSubtypeRegistry
            .getAll()
            .filter((item) => isOdoo === isOdooKey(item.chartType));
        this.chartTypeByCategories = groupByCategory(registryItems);
    },
});
