import * as spreadsheet from "@odoo/o-spreadsheet";
import {Component, onWillStart, onWillUpdateProps, useState} from "@odoo/owl";
import {Domain} from "@web/core/domain";
import {DomainSelector} from "@web/core/domain_selector/domain_selector";
import {DomainSelectorDialog} from "@web/core/domain_selector_dialog/domain_selector_dialog";
import {_t} from "@web/core/l10n/translation";
import {formatDate} from "@web/core/l10n/dates";
import {useService} from "@web/core/utils/hooks";

const {DateTime} = luxon;
const {sidePanelRegistry, topbarMenuRegistry, pivotSidePanelRegistry} =
    spreadsheet.registries;

topbarMenuRegistry.addChild("data_sources", ["data"], (env) => {
    let sequence = 53;
    const lists = env.model.getters.getListIds().map((listId, index) => ({
        id: `data_source_list_${listId}`,
        name: env.model.getters.getListDisplayName(listId),
        sequence: sequence++,
        execute: (child_env) => {
            child_env.model.dispatch("SELECT_ODOO_LIST", {listId: listId});
            child_env.openSidePanel("ListPanel", {listId});
        },
        icon: "spreadsheet_oca.ListIcon",
        separator: index === env.model.getters.getListIds().length - 1,
    }));
    return lists.concat([
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
        this.PivotDataSource = this.env.model.getters.getPivot(this.props.pivotId);
        this.modelLabel = await this.PivotDataSource.getModelLabel();
    }
    get domain() {
        return new Domain(this.props.pivotDefinition.domain).toString();
    }
    get pivotDimensions() {
        const {rows = [], columns = []} = this.props.pivotDefinition;
        return [...rows, ...columns].map((dim) => {
            const label = dim.displayName || dim.fieldName;
            return dim.granularity ? `${label} (${dim.granularity})` : label;
        });
    }
    get sortInformation() {
        const sortedColumn = this.props.pivotDefinition.sortedColumn;
        const orderTranslate =
            sortedColumn.order === "asc" ? _t("ascending") : _t("descending");

        let label = null;
        if (sortedColumn.measure) {
            const measure = this.PivotDataSource.getMeasure(sortedColumn.measure);
            label = measure ? measure.displayName : sortedColumn.measure;
        } else if (sortedColumn.groupBy) {
            label = this.PivotDataSource.getFormattedGroupBy(sortedColumn.groupBy);
        }
        return `${label} (${orderTranslate})`;
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
        const pivotId = this.props.pivotId;
        const {type} = this.env.model.getters.getPivotCoreDefinition(pivotId);
        const position = this.env.model.getters.getActivePosition();
        let table = null;
        if (type === "ODOO") {
            const dataSource = this.env.model.getters.getPivot(pivotId);
            const model = await dataSource.copyModelWithOriginalDomain();
            table = model.getTableStructure().export();
        } else {
            table = this.env.model.getters
                .getPivot(pivotId)
                .getTableStructure()
                .export();
        }
        this.env.model.dispatch("INSERT_PIVOT_WITH_TABLE", {
            ...position,
            pivotId,
            table,
            pivotMode: "static",
        });
        this.env.model.dispatch("REFRESH_PIVOT", {id: pivotId});
    }
    async insertDynamicPivot() {
        const pivotId = this.props.pivotId;
        const {type} = this.env.model.getters.getPivotCoreDefinition(pivotId);
        const position = this.env.model.getters.getActivePosition();
        let table = null;
        if (type === "ODOO") {
            const dataSource = this.env.model.getters.getPivot(this.props.pivotId);
            const model = await dataSource.copyModelWithOriginalDomain();
            table = model.getTableStructure().export();
        } else {
            table = this.env.model.getters
                .getPivot(this.props.pivotId)
                .getTableStructure()
                .export();
        }
        this.env.model.dispatch("INSERT_PIVOT_WITH_TABLE", {
            ...position,
            pivotId,
            table,
            pivotMode: "dynamic",
        });
        this.env.model.dispatch("REFRESH_PIVOT", {id: pivotId});
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
        return this.props.pivotId;
    }
    get pivotType() {
        return this.env.model.getters.getPivotCoreDefinition(this.pivotId).type;
    }
    get pivotDefinition() {
        const dataSource = this.env.model.getters.getPivot(this.pivotId);
        return dataSource ? dataSource.definition || {} : {};
    }
}

PivotPanel.template = "spreadsheet_oca.PivotPanel";
PivotPanel.components = {
    PivotPanelDisplay,
};

pivotSidePanelRegistry.add("ODOO", {
    editor: PivotPanel,
});

export class ListPanelDisplay extends Component {
    setup() {
        this.state = useState({listRows: undefined});
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
    async insertList() {
        const listId = this.props.listId;
        const zone = this.env.model.getters.getSelectedZone();
        const dataSource = await this.env.model.getters.getAsyncListDataSource(listId);
        const totalRows = parseInt(this.state.listRows, 10) || dataSource.maxPosition;
        const list = this.env.model.getters.getListDefinition(listId);
        const sheetId = this.env.model.getters.getActiveSheetId();
        const columns = list.columns.map((name) => ({
            name,
            type: dataSource.getField(name).type,
        }));
        this.env.model.dispatch("RE_INSERT_ODOO_LIST_WITH_TABLE", {
            sheetId: sheetId,
            col: zone.left,
            row: zone.top,
            id: listId,
            linesNumber: totalRows,
            columns: columns,
        });
    }
    delete() {
        this.env.askConfirmation(
            _t("Are you sure you want to delete this list?"),
            () => {
                this.env.model.dispatch("REMOVE_ODOO_LIST", {
                    listId: this.props.listId,
                });
                this.env.openSidePanel("ListPanel", {});
            }
        );
    }
}

ListPanelDisplay.template = "spreadsheet_oca.ListPanelDisplay";
ListPanelDisplay.components = {
    DomainSelector,
};
ListPanelDisplay.props = {
    listId: String,
    listDefinition: Object,
};

export class ListPanel extends Component {
    get listId() {
        return this.props.listId;
    }
    get listDefinition() {
        return this.env.model.getters.getListDefinition(this.listId) || {};
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
