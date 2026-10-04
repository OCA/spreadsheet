import * as spreadsheet from "@odoo/o-spreadsheet";
import {
    Component,
    onWillStart,
    onWillUpdateProps,
    proxy,
    signal,
    t,
    usePlugin,
    useProps,
} from "@odoo/owl";
import {DebugModePlugin} from "@web/core/debug_mode_plugin";
import {Domain} from "@web/core/domain";
import {DomainSelector} from "@web/core/domain_selector/domain_selector";
import {DomainSelectorDialog} from "@web/core/domain_selector_dialog/domain_selector_dialog";
import {ODOO_AGGREGATORS} from "@spreadsheet/pivot/pivot_helpers";
import {_t} from "@web/core/l10n/translation";
import {formatDate} from "@web/core/l10n/dates";
import {useService} from "@web/core/utils/hooks";

const {DateTime} = luxon;
const {PivotTitleSection, PivotLayoutConfigurator} = spreadsheet.components;
const {useLocalStore, PivotSidePanelStore} = spreadsheet.stores;
const {sidePanelRegistry, topbarMenuRegistry, pivotSidePanelRegistry} =
    spreadsheet.registries;

topbarMenuRegistry.addChild("data_sources", ["data"], (env) => {
    let sequence = 53;
    const lists = env.model.getters.getListIds().map((listId, index) => ({
        id: `data_source_list_${listId}`,
        name: env.model.getters.getListDisplayName(listId),
        sequence: sequence++,
        execute: (child_env) => {
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

export class PivotLayoutConfiguratorWithAggregators extends PivotLayoutConfigurator {
    setup() {
        super.setup();
        this.AGGREGATORS = ODOO_AGGREGATORS;
    }
}

export class PivotTitleSectionInsertion extends PivotTitleSection {
    get cogWheelMenuItems() {
        const res = super.cogWheelMenuItems;
        res.push(
            {
                name: _t("Re-insert Dynamic"),
                icon: "o-spreadsheet-Icon.INSERT_PIVOT",
                execute: (env) => this.reinsertTable(env, "dynamic"),
            },
            {
                name: _t("Re-insert Static"),
                icon: "o-spreadsheet-Icon.INSERT_PIVOT",
                execute: (env) => this.reinsertTable(env, "static"),
            }
        );
        return res;
    }
    reinsertTable(env, mode) {
        const zone = env.model.getters.getSelectedZone();
        const pivot = env.model.getters.getPivot(this.props.pivotId);
        const table = (
            mode === "dynamic"
                ? pivot.getCollapsedTableStructure()
                : pivot.getExpandedTableStructure()
        ).export();
        env.model.dispatch("INSERT_PIVOT_WITH_TABLE", {
            pivotId: this.props.pivotId,
            table,
            col: zone.left,
            row: zone.top,
            sheetId: env.model.getters.getActiveSheetId(),
            pivotMode: mode,
        });
        env.model.dispatch("REFRESH_PIVOT", {id: this.props.pivotId});
    }
}

export class PivotPanelDisplay extends Component {
    static template = "spreadsheet_oca.PivotPanelDisplay";
    static components = {
        DomainSelector,
        PivotTitleSectionInsertion,
        PivotLayoutConfiguratorWithAggregators,
    };
    props = useProps({
        pivotId: t.string(),
    });
    pivotPanelRef = signal.ref();

    setup() {
        this.dialog = useService("dialog");
        this.debugMode = usePlugin(DebugModePlugin);
        this.store = useLocalStore(PivotSidePanelStore, this.props.pivotId);
        onWillStart(this.modelData.bind(this));
        onWillUpdateProps(this.modelData.bind(this));
    }
    async modelData() {
        this.PivotDataSource = this.env.model.getters.getPivot(this.props.pivotId);
        this.modelLabel = await this.PivotDataSource.getModelLabel();
    }
    get domain() {
        return new Domain(this.store.definition.domain).toString();
    }
    get sortInformation() {
        const sortedColumn = this.store.definition.sortedColumn;
        const orderTranslate =
            sortedColumn.order === "asc" ? _t("ascending") : _t("descending");
        const measure = this.store.definition.measures.find(
            (m) => m.fieldName === sortedColumn.measure
        );
        const label = this.PivotDataSource.getMeasure(measure.id).displayName;
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
            resModel: this.store.definition.model,
            domain: this.domain,
            readonly: false,
            isDebugMode: this.debugMode.isActive(),
            onConfirm: this.onSelectDomain.bind(this),
        });
    }
    updateDimensions(dimensions) {
        this.store.update(dimensions);
    }
    onSelectDomain(domain) {
        this.store.update({domain});
    }
    getScrollableContainerEl() {
        return this.pivotPanelRef();
    }
    flipAxis() {
        const dimensions = {
            rows: this.store.definition.columns,
            columns: this.store.definition.rows,
        };
        this.updateDimensions(dimensions);
    }
}

export class PivotPanel extends Component {
    static template = "spreadsheet_oca.PivotPanel";
    static components = {PivotPanelDisplay};
    props = useProps();

    get pivotId() {
        return this.props.pivotId;
    }
    get pivotType() {
        return this.env.model.getters.getPivotCoreDefinition(this.pivotId).type;
    }
}

pivotSidePanelRegistry.add("ODOO", {
    editor: PivotPanel,
});

export class ListPanelDisplay extends Component {
    static template = "spreadsheet_oca.ListPanelDisplay";
    static components = {DomainSelector};
    props = useProps({
        listId: t.string(),
        listDefinition: t.object(),
    });

    setup() {
        this.state = proxy({listRows: undefined});
        this.dialog = useService("dialog");
        this.debugMode = usePlugin(DebugModePlugin);
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
            isDebugMode: this.debugMode.isActive(),
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
        this.env.model.dispatch("RE_INSERT_ODOO_LIST_WITH_TABLE", {
            sheetId: sheetId,
            col: zone.left,
            row: zone.top,
            listId,
            linesNumber: totalRows,
            columns: list.columns.filter((column) => !column.hidden),
            mode: "static",
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

export class ListPanel extends Component {
    static template = "spreadsheet_oca.ListPanel";
    static components = {ListPanelDisplay};
    props = useProps();

    get listId() {
        return this.props.listId;
    }
    get listDefinition() {
        return this.env.model.getters.getListDefinition(this.listId) || {};
    }
}

sidePanelRegistry.add("ListPanel", {
    title: "List information",
    Body: ListPanel,
});
