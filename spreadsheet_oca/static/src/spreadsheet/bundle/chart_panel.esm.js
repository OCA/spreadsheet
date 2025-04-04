/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";

const { chartRegistry } = spreadsheet.registries;
const { ChartPanel } = spreadsheet.components;
export function isOdooKey(code) {
  return code.startsWith("odoo_");
}

patch(ChartPanel.prototype, {
  get chartTypes() {
    return this.filterChartTypes(isOdooKey(this.getChartDefinition().type));
  },

  filterChartTypes(isOdoo) {
    var result = {};
    for (const key of chartRegistry.getKeys()) {
      if ((isOdoo && isOdooKey(key)) || (!isOdoo && !isOdooKey(key))) {
        result[key] = chartRegistry.get(key).name;
      }
    }
    return result;
  },
  onTypeChange(type) {
    if (isOdooKey(this.getChartDefinition().type)) {
      const definition = {
        stacked: false,
        verticalAxisPosition: "left",
        ...this.env.model.getters.getChartDefinition(this.figureId),
        type,
      };
      this.env.model.dispatch("UPDATE_CHART", {
        definition,
        id: this.figureId,
        sheetId: this.env.model.getters.getActiveSheetId(),
      });
    } else {
      super.onTypeChange(type);
    }
  },
});
