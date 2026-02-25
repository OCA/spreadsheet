import * as spreadsheet from "@odoo/o-spreadsheet";

import {Domain} from "@web/core/domain";
import {Many2XAutocomplete} from "@web/views/fields/relational_utils";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";

const {chartSidePanelComponentRegistry, chartSubtypeRegistry} = spreadsheet.registries;
const {PieChartDesignPanel} = spreadsheet.components;
const {Component} = owl;

export class OdooPanel extends Component {
    setup() {
        this.menus = useService("menu");
    }
    get menuProps() {
        const menu = this.env.model.getters.getChartOdooMenu(this.props.figureId);
        var result = {
            fieldString: _t("Menu Items"),
            resModel: "ir.ui.menu",
            update: this.updateMenu.bind(this),
            activeActions: {},
            getDomain: this.getDomain.bind(this),
        };
        if (menu) {
            result.value = menu.name;
            result.id = menu.id;
        }
        return result;
    }
    getDomain() {
        const menus = this.menus
            .getAll()
            .map((menu) => menu.id)
            .filter((menuId) => menuId !== "root");
        return [["id", "in", menus]];
    }
    get menuId() {
        const menu = this.env.model.getters.getChartOdooMenu(this.props.figureId);
        if (menu) {
            return [menu.id, menu.name];
        }
        return false;
    }
    updateMenu(menuId) {
        if (!menuId) {
            this.env.model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                chartId: this.props.figureId,
                odooMenuId: false,
            });
            return;
        }
        const menu = this.env.model.getters.getIrMenu(menuId[0].id);
        this.env.model.dispatch("LINK_ODOO_MENU_TO_CHART", {
            chartId: this.props.figureId,
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
        this.props.updateChart(this.props.figureId, {
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
    });

chartSubtypeRegistry.add("odoo_line", {
    matcher: (definition) =>
        definition.type === "odoo_line" && !definition.stacked && !definition.fillArea,
    subtypeDefinition: {stacked: false, fillArea: false},
    displayName: _t("Line"),
    chartSubtype: "odoo_line",
    chartType: "odoo_line",
    category: "line",
    preview: "o-spreadsheet-ChartPreview.LINE_CHART",
});
chartSubtypeRegistry.add("odoo_stacked_line", {
    matcher: (definition) =>
        definition.type === "odoo_line" && definition.stacked && !definition.fillArea,
    subtypeDefinition: {stacked: true, fillArea: false},
    displayName: _t("Stacked Line"),
    chartSubtype: "odoo_stacked_line",
    chartType: "odoo_line",
    category: "line",
    preview: "o-spreadsheet-ChartPreview.STACKED_LINE_CHART",
});
chartSubtypeRegistry.add("odoo_area", {
    matcher: (definition) =>
        definition.type === "odoo_line" && !definition.stacked && definition.fillArea,
    subtypeDefinition: {stacked: false, fillArea: true},
    displayName: _t("Area"),
    chartSubtype: "odoo_area",
    chartType: "odoo_line",
    category: "area",
    preview: "o-spreadsheet-ChartPreview.AREA_CHART",
});
chartSubtypeRegistry.add("odoo_stacked_area", {
    matcher: (definition) =>
        definition.type === "odoo_line" && definition.stacked && definition.fillArea,
    subtypeDefinition: {stacked: true, fillArea: true},
    displayName: _t("Stacked Area"),
    chartSubtype: "odoo_stacked_area",
    chartType: "odoo_line",
    category: "area",
    preview: "o-spreadsheet-ChartPreview.STACKED_AREA_CHART",
});
chartSubtypeRegistry.add("odoo_bar", {
    matcher: (definition) => definition.type === "odoo_bar" && !definition.stacked,
    subtypeDefinition: {stacked: false},
    displayName: _t("Column"),
    chartSubtype: "odoo_bar",
    chartType: "odoo_bar",
    category: "column",
    preview: "o-spreadsheet-ChartPreview.COLUMN_CHART",
});
chartSubtypeRegistry.add("odoo_stacked_bar", {
    matcher: (definition) => definition.type === "odoo_bar" && definition.stacked,
    subtypeDefinition: {stacked: true},
    displayName: _t("Stacked Column"),
    chartSubtype: "odoo_stacked_bar",
    chartType: "odoo_bar",
    category: "column",
    preview: "o-spreadsheet-ChartPreview.STACKED_COLUMN_CHART",
});
chartSubtypeRegistry.add("odoo_pie", {
    displayName: _t("Pie"),
    chartSubtype: "odoo_pie",
    chartType: "odoo_pie",
    category: "pie",
    preview: "o-spreadsheet-ChartPreview.PIE_CHART",
});
