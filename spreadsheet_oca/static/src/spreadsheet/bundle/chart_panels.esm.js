/** @odoo-module */

import {Domain} from "@web/core/domain";
import {Many2OneField} from "@web/views/fields/many2one/many2one_field";
import {patch} from "@web/core/utils/patch";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import {useService} from "@web/core/utils/hooks";

const {LineBarPieConfigPanel, ScorecardChartConfigPanel, GaugeChartConfigPanel} =
    spreadsheet.components;

const menuChartProps = {
    setup() {
        this._super.apply(this, arguments);
        this.menus = useService("menu");
    },
    get menuId() {
        const menu = this.env.model.getters.getChartOdooMenu(this.props.figureId);
        if (menu) {
            return [menu.id, menu.name];
        }
        return false;
    },
    updateMenu(menuId) {
        if (!menuId) {
            this.env.model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                chartId: this.props.figureId,
                odooMenuId: false,
            });
            return;
        }
        const menu = this.env.model.getters.getIrMenu(menuId[0]);
        this.env.model.dispatch("LINK_ODOO_MENU_TO_CHART", {
            chartId: this.props.figureId,
            odooMenuId: menu.xmlid || menu.id,
        });
    },
    get record() {
        const menus = this.menus
            .getAll()
            .map((menu) => menu.id)
            .filter((menuId) => menuId !== "root");
        return {
            getFieldDomain: function () {
                return new Domain([["id", "in", menus]]);
            },
            getFieldContext: function () {
                return {};
            },
        };
    },
};

patch(
    LineBarPieConfigPanel.prototype,
    "spreadsheet_oca.LineBarPieConfigPanel",
    menuChartProps
);
LineBarPieConfigPanel.components = {
    ...LineBarPieConfigPanel.components,
    Many2OneField,
};

patch(
    ScorecardChartConfigPanel.prototype,
    "spreadsheet_oca.ScorecardChartConfigPanel",
    menuChartProps
);
ScorecardChartConfigPanel.components = {
    ...ScorecardChartConfigPanel.components,
    Many2OneField,
};

patch(
    GaugeChartConfigPanel.prototype,
    "spreadsheet_oca.GaugeChartConfigPanel",
    menuChartProps
);
GaugeChartConfigPanel.components = {
    ...GaugeChartConfigPanel.components,
    Many2OneField,
};
