import * as spreadsheet from "@odoo/o-spreadsheet";

import {Domain} from "@web/core/domain";
import {Many2XAutocomplete} from "@web/views/fields/relational_utils";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";

const {chartSidePanelComponentRegistry} = spreadsheet.registries;
const {
    PieChartDesignPanel,
    ChartWithAxisDesignPanel,
    ComboChartDesignPanel,
    FunnelChartDesignPanel,
    GeoChartDesignPanel,
    RadarChartDesignPanel,
    SunburstChartDesignPanel,
    TreeMapChartDesignPanel,
    WaterfallChartDesignPanel,
} = spreadsheet.components;
const {Component} = owl;

export class OdooPanel extends Component {
    setup() {
        this.menus = useService("menu");
    }
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
    }
    getDomain() {
        const menus = this.menus
            .getAll()
            .map((menu) => menu.id)
            .filter((menuId) => menuId !== "root");
        return [["id", "in", menus]];
    }
    get chartId() {
        return this.props.chartId;
    }
    get menuId() {
        const menu = this.env.model.getters.getChartOdooMenu(this.chartId);
        if (menu) {
            return [menu.id, menu.name];
        }
        return false;
    }
    updateMenu(menuId) {
        if (!menuId) {
            this.env.model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                chartId: this.chartId,
                odooMenuId: false,
            });
            return;
        }
        const menu = this.env.model.getters.getIrMenu(menuId[0].id);
        this.env.model.dispatch("LINK_ODOO_MENU_TO_CHART", {
            chartId: this.chartId,
            odooMenuId: menu.xmlid || menu.id,
        });
    }
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
    }
}
OdooPanel.template = "spreadsheet_oca.OdooPanel";
OdooPanel.components = {Many2XAutocomplete};

class OdooStackablePanel extends OdooPanel {
    onChangeStacked(ev) {
        this.props.updateChart(this.chartId, {
            stacked: ev.target.checked,
        });
    }
}
OdooStackablePanel.template = "spreadsheet_oca.OdooStackablePanel";

chartSidePanelComponentRegistry
    .add("odoo_line", {
        configuration: OdooStackablePanel,
        design: PieChartDesignPanel,
    })
    .add("odoo_bar", {
        configuration: OdooStackablePanel,
        design: PieChartDesignPanel,
    })
    .add("odoo_pie", {
        configuration: OdooPanel,
        design: PieChartDesignPanel,
    })
    .add("odoo_combo", {
        configuration: OdooPanel,
        design: ComboChartDesignPanel,
    })
    .add("odoo_scatter", {
        configuration: OdooStackablePanel,
        design: ChartWithAxisDesignPanel,
    })
    .add("odoo_pyramid", {
        configuration: OdooPanel,
        design: ChartWithAxisDesignPanel,
    })
    .add("odoo_waterfall", {
        configuration: OdooPanel,
        design: WaterfallChartDesignPanel,
    })
    .add("odoo_radar", {
        configuration: OdooPanel,
        design: RadarChartDesignPanel,
    })
    .add("odoo_sunburst", {
        configuration: OdooPanel,
        design: SunburstChartDesignPanel,
    })
    .add("odoo_treemap", {
        configuration: OdooPanel,
        design: TreeMapChartDesignPanel,
    })
    .add("odoo_geo", {
        configuration: OdooPanel,
        design: GeoChartDesignPanel,
    })
    .add("odoo_funnel", {
        configuration: OdooPanel,
        design: FunnelChartDesignPanel,
    });
