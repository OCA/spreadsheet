/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { Domain } from "@web/core/domain";

import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const {
  LineBarPieConfigPanel,
  ScorecardChartConfigPanel,
  GaugeChartConfigPanel,
} = spreadsheet.components;

const menuChartProps = {
  setup() {
    super.setup(...arguments);
    this.menus = useService("menu");
  },
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
  },

  getDomain() {
    const menus = this.menus
      .getAll()
      .map((menu) => menu.id)
      .filter((menuId) => menuId !== "root");
    return [["id", "in", menus]];
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
    const menu = this.env.model.getters.getIrMenu(menuId[0].id);
    console.log(menu);
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

patch(LineBarPieConfigPanel.prototype, menuChartProps);
LineBarPieConfigPanel.components = {
  ...LineBarPieConfigPanel.components,
  Many2XAutocomplete,
};

patch(ScorecardChartConfigPanel.prototype, menuChartProps);
ScorecardChartConfigPanel.components = {
  ...ScorecardChartConfigPanel.components,
  Many2XAutocomplete,
};

patch(GaugeChartConfigPanel.prototype, menuChartProps);
GaugeChartConfigPanel.components = {
  ...GaugeChartConfigPanel.components,
  Many2XAutocomplete,
};
