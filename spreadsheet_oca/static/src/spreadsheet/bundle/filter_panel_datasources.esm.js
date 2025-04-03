/** @odoo-module **/

import * as spreadsheet from "@odoo/o-spreadsheet";
import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import {
  makeDynamicCols,
  makeDynamicRows,
} from "../utils/dynamic_generators.esm";
import { Domain } from "@web/core/domain";
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { _t } from "@web/core/l10n/translation";
import { formatDate } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;
const { sidePanelRegistry, topbarMenuRegistry } = spreadsheet.registries;

topbarMenuRegistry.addChild("data_sources", ["data"], (env) => {
  let sequence = 100;
  const children = env.model.getters.getPivotIds().map((pivotId, index) => ({
    id: `data_source_pivot_ ${pivotId}`,
    name: env.model.getters.getPivotDisplayName(pivotId),
    sequence: sequence++,
    execute: (child_env) => {
      child_env.model.dispatch("SELECT_PIVOT", {
        pivotId: pivotId,
      });
      child_env.openSidePanel("PivotPanel", {});
    },
    icon: "spreadsheet_oca.PivotIcon",
    separator: index === env.model.getters.getPivotIds().length - 1,
  }));
  const lists = env.model.getters.getListIds().map((listId, index) => ({
    id: `data_source_list_${listId}`,
    name: env.model.getters.getListDisplayName(listId),
    sequence: sequence++,
    execute: (child_env) => {
      child_env.model.dispatch("SELECT_ODOO_LIST", { listId: listId });
      child_env.openSidePanel("ListPanel", {});
    },
    icon: "spreadsheet_oca.ListIcon",
    separator: index === env.model.getters.getListIds().length - 1,
  }));
  return children.concat(lists).concat([
    {
      id: "refresh_all_data",
      name: _t("Refresh all data"),
      sequence: 110,
      execute: (child_env) => {
        child_env.model.dispatch("REFRESH_ALL_DATA_SOURCES");
      },
      separator: true,
    },
  ]);
});

export class PivotPanelDisplay extends Component {
  setup() {
    this.dialog = useService("dialog");
    onWillStart(this.modelData.bind(this));
    onWillUpdateProps(this.modelData.bind(this));
  }
  async modelData() {
    this.PivotDataSource = await this.env.model.getters.getAsyncPivotDataSource(
      this.props.pivotId
    );
    this.modelLabel = await this.PivotDataSource.getModelLabel();
  }
  get domain() {
    return new Domain(this.props.pivotDefinition.domain).toString();
  }
  get pivotDimensions() {
    return [
      ...this.props.pivotDefinition.rowGroupBys,
      ...this.props.pivotDefinition.colGroupBys,
    ].map((fieldName) => this.PivotDataSource.getFormattedGroupBy(fieldName));
  }
  get sortInformation() {
    const sortedColumn = this.props.pivotDefinition.sortedColumn;
    const orderTranslate =
      sortedColumn.order === "asc" ? _t("ascending") : _t("descending");
    const GroupByDisplayLabel = this.PivotDataSource.getGroupByDisplayLabel(
      "measure",
      sortedColumn.measure
    );
    return `${GroupByDisplayLabel} (${orderTranslate})`;
  }
  get lastUpdate() {
    const lastUpdate = this.PivotDataSource.lastUpdate;
    if (lastUpdate) {
      return formatDate(DateTime.fromMillis(lastUpdate));
    }
    return _t("not updated");
  }
  editDomain() {
    this.dialog.add(DomainSelectorDialog, {
      resModel: this.props.pivotDefinition.model,
      domain: this.domain,
      readonly: false,
      isDebugMode: Boolean(this.env.debug),
      onConfirm: this.onSelectDomain.bind(this),
    });
  }
  onSelectDomain(domain) {
    this.env.model.dispatch("UPDATE_ODOO_PIVOT_DOMAIN", {
      pivotId: this.props.pivotId,
      domain: new Domain(domain).toList(),
    });
  }
  async insertPivot() {
    const datasourceModel = await this.env.model.getters
      .getPivotDataSource(this.props.pivotId)
      .copyModelWithOriginalDomain();
    const tableStructure = datasourceModel.getTableStructure().export();
    const selectedZone = this.env.model.getters.getSelectedZone();
    this.env.model.dispatch("RE_INSERT_PIVOT", {
      id: this.props.pivotId,
      col: selectedZone.left,
      row: selectedZone.top,
      sheetId: this.env.model.getters.getActiveSheetId(),
      table: tableStructure,
    });
    this.env.model.dispatch("REFRESH_PIVOT", { id: this.props.pivotId });
  }

  async insertDynamicPivot() {
    const datasourceModel = await this.env.model.getters
      .getPivotDataSource(this.props.pivotId)
      .copyModelWithOriginalDomain();
    var { cols, rows, measures } = datasourceModel.getTableStructure().export();
    const { dynamic_rows, number_of_rows, dynamic_cols, number_of_cols } =
      await new Promise((resolve) => {
        this.dialog.add(
          FormViewDialog,
          {
            title: _t("Select the quantity of rows"),
            resModel: "spreadsheet.select.row.number",
            context: {
              default_can_have_dynamic_cols: Boolean(cols[0][0].fields.length),
            },
            onRecordSaved: async (record) => {
              resolve({
                dynamic_rows: record.data.dynamic_rows,
                number_of_rows: record.data.number_of_rows,
                dynamic_cols: record.data.dynamic_cols,
                number_of_cols: record.data.number_of_cols,
              });
            },
          },
          { onClose: () => resolve(false) }
        );
      });
    if (!dynamic_rows && !dynamic_cols) {
      return;
    }
    if (dynamic_rows) {
      const indentations = rows.map((r) => r.indent);
      const max_indentation = Math.max(...indentations);
      rows = makeDynamicRows(
        this.props.pivotDefinition.rowGroupBys,
        number_of_rows,
        1,
        max_indentation
      );
    }
    if (dynamic_cols) {
      cols = makeDynamicCols(
        this.props.pivotDefinition.colGroupBys,
        number_of_cols,
        this.props.pivotDefinition.measures
      );
    }
    const table = {
      cols,
      rows,
      measures,
    };
    const selectedZone = this.env.model.getters.getSelectedZone();
    this.env.model.dispatch("RE_INSERT_PIVOT", {
      id: this.props.pivotId,
      col: selectedZone.left,
      row: selectedZone.top,
      sheetId: this.env.model.getters.getActiveSheetId(),
      table,
    });
    this.env.model.dispatch("REFRESH_PIVOT", { id: this.props.pivotId });
  }
  delete() {
    this.env.askConfirmation(
      _t("Are you sure you want to delete this pivot?"),
      () => {
        this.env.model.dispatch("REMOVE_PIVOT", {
          pivotId: this.props.pivotId,
        });
      }
    );
  }
}

PivotPanelDisplay.template = "spreadsheet_oca.PivotPanelDisplay";
PivotPanelDisplay.components = {
  DomainSelector,
};
PivotPanelDisplay.properties = {
  pivotId: String,
  pivotDefinition: Object,
};

export class PivotPanel extends Component {
  get pivotId() {
    return this.env.model.getters.getSelectedPivotId();
  }
  get pivotDefinition() {
    return this.env.model.getters.getPivotDefinition(this.pivotId);
  }
}

PivotPanel.template = "spreadsheet_oca.PivotPanel";
PivotPanel.components = {
  PivotPanelDisplay,
};

sidePanelRegistry.add("PivotPanel", {
  title: "Pivot table information",
  Body: PivotPanel,
});

export class ListPanelDisplay extends Component {
  setup() {
    this.dialog = useService("dialog");
    onWillStart(this.modelData.bind(this));
    onWillUpdateProps(this.modelData.bind(this));
  }
  async modelData() {
    this.ListDataSource = await this.env.model.getters.getAsyncListDataSource(
      this.props.listId
    );
    this.modelLabel = await this.ListDataSource.getModelLabel();
  }
  get domain() {
    return new Domain(this.props.listDefinition.domain).toString();
  }
  get lastUpdate() {
    const lastUpdate = this.ListDataSource.lastUpdate;
    if (lastUpdate) {
      return formatDate(DateTime.fromMillis(lastUpdate));
    }
    return _t("not updated");
  }
  editDomain() {
    this.dialog.add(DomainSelectorDialog, {
      resModel: this.props.listDefinition.model,
      domain: this.domain,
      readonly: false,
      isDebugMode: Boolean(this.env.debug),
      onConfirm: this.onSelectDomain.bind(this),
    });
  }
  onSelectDomain(domain) {
    this.env.model.dispatch("UPDATE_ODOO_LIST_DOMAIN", {
      listId: this.props.listId,
      domain: new Domain(domain).toList(),
    });
  }
  delete() {
    this.env.askConfirmation(
      _t("Are you sure you want to delete this list?"),
      () => {
        this.env.model.dispatch("REMOVE_ODOO_LIST", {
          listId: this.props.listId,
        });
      }
    );
  }
}

ListPanelDisplay.template = "spreadsheet_oca.ListPanelDisplay";
ListPanelDisplay.components = {
  DomainSelector,
};
ListPanelDisplay.properties = {
  listId: String,
  listDefinition: Object,
};

export class ListPanel extends Component {
  get listId() {
    return this.env.model.getters.getSelectedListId();
  }
  get listDefinition() {
    return this.env.model.getters.getListDefinition(this.listId);
  }
}

ListPanel.template = "spreadsheet_oca.ListPanel";
ListPanel.components = {
  ListPanelDisplay,
};

sidePanelRegistry.add("ListPanel", {
  title: "List information",
  Body: ListPanel,
});
