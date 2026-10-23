import * as spreadsheet from "@odoo/o-spreadsheet";
import {Domain} from "@web/core/domain";
import {Many2XAutocomplete} from "@web/views/fields/relational_utils";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

const {
    GenericChartConfigPanel,
    LineConfigPanel,
    BarConfigPanel,
    ScorecardChartConfigPanel,
    GaugeChartConfigPanel,
} = spreadsheet.components;

const menuChartProps = () => ({
    setup() {
        super.setup(...arguments);
        this.menus = useService("menu");
    },
    get menuProps() {
        return {
            fieldString: _t("Menu Items"),
            resModel: "ir.ui.menu",
            update: this.updateMenu.bind(this),
            activeActions: {},
            getDomain: this.getDomain.bind(this),
            placeholder: _t("Select a menu..."),
            value: this.menuId ? this.menuId[1] : "",
        };
    },

    getDomain() {
        const menus = this.menus
            .getAll()
            .map((menu) => menu.id)
            .filter((menuId) => menuId !== "root");
        return [["id", "in", menus]];
    },
    get menuId() {
        const odooLink = this.env.model.getters.getChartOdooLink(this.props.chartId);
        if (odooLink && odooLink.type === "odooMenu") {
            const menu = this.env.model.getters.getIrMenu(odooLink.odooMenuId);
            if (menu) {
                return [menu.id, menu.name];
            }
        }
        return false;
    },
    updateMenu(menuId) {
        if (!menuId) {
            this.env.model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
                chartId: this.props.chartId,
                odooLink: undefined,
            });
            return;
        }
        const menu = this.env.model.getters.getIrMenu(menuId[0].id);
        this.env.model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
            chartId: this.props.chartId,
            odooLink: {type: "odooMenu", odooMenuId: menu.xmlid || menu.id},
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
});

// LineConfigPanel and BarConfigPanel extend GenericChartConfigPanel
for (const ConfigPanel of [
    GenericChartConfigPanel,
    ScorecardChartConfigPanel,
    GaugeChartConfigPanel,
]) {
    patch(ConfigPanel.prototype, menuChartProps());
}
for (const ConfigPanel of [
    GenericChartConfigPanel,
    LineConfigPanel,
    BarConfigPanel,
    ScorecardChartConfigPanel,
    GaugeChartConfigPanel,
]) {
    ConfigPanel.components = {
        ...ConfigPanel.components,
        Many2XAutocomplete,
    };
}
