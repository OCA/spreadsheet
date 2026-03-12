import * as spreadsheet from "@odoo/o-spreadsheet";
import {Component, onWillStart, onWillUpdateProps, useRef, useState} from "@odoo/owl";
import {Domain} from "@web/core/domain";
import {DomainSelector} from "@web/core/domain_selector/domain_selector";
import {DomainSelectorDialog} from "@web/core/domain_selector_dialog/domain_selector_dialog";
import {_t} from "@web/core/l10n/translation";
import {formatDate} from "@web/core/l10n/dates";
import {useService} from "@web/core/utils/hooks";
import {ODOO_AGGREGATORS} from "@spreadsheet/pivot/pivot_helpers";

const {DateTime} = luxon;
const {PivotTitleSection, PivotLayoutConfigurator} = spreadsheet.components;
const {useLocalStore, PivotSidePanelStore} = spreadsheet.stores;
const {sidePanelRegistry, topbarMenuRegistry, pivotSidePanelRegistry} =
    spreadsheet.registries;

/**
 * Scan every cell in every sheet to find the top-left anchor position of each
 * pivot table. Returns a Map<pivotId, {sheetId, col, row}>.
 *
 * @param {Object} getters  o-spreadsheet getters
 * @returns {Map<string, {sheetId: string, col: number, row: number}>}
 */
function _findPivotAnchors(getters) {
    const anchors = new Map();
    for (const sheetId of getters.getSheetIds()) {
        const cells = getters.getCells(sheetId);
        for (const cellId in cells) {
            const {col, row} = getters.getCellPosition(cellId);
            const pivotId = getters.getPivotIdFromPosition({sheetId, col, row});
            if (!pivotId) {
                continue;
            }
            const current = anchors.get(pivotId);
            if (
                !current ||
                row < current.row ||
                (row === current.row && col < current.col)
            ) {
                anchors.set(pivotId, {sheetId, col, row});
            }
        }
    }
    return anchors;
}

/**
 * Reload all pivot data sources from Odoo concurrently, then re-insert each
 * pivot table at its current position using the fresh data.
 *
 * Also dispatches REFRESH_ALL_DATA_SOURCES so that lists and charts are
 * handled by the CE plugin (which refreshes their data sources independently).
 *
 * @param {Object} env  o-spreadsheet environment
 */
async function _refreshAndReinsertAllPivots(env) {
    const getters = env.model.getters;
    const pivotIds = getters.getPivotIds();

    // Snapshot pivot positions before reload (cell layout doesn't change)
    const anchors = _findPivotAnchors(getters);

    // Reload all pivots concurrently for speed
    await Promise.all(pivotIds.map((id) => getters.getPivot(id).load({reload: true})));

    // Re-insert each pivot at its anchor with the freshly-loaded table structure
    for (const pivotId of pivotIds) {
        const anchor = anchors.get(pivotId);
        if (!anchor) {
            continue; // Pivot was never inserted into a sheet — skip
        }
        const table = getters.getPivot(pivotId).getTableStructure().export();
        env.model.dispatch("INSERT_PIVOT_WITH_TABLE", {
            pivotId,
            table,
            col: anchor.col,
            row: anchor.row,
            sheetId: anchor.sheetId,
            pivotMode: "dynamic",
        });
    }

    // Let the CE plugin handle lists and charts (REFRESH_ALL_DATA_SOURCES)
    env.model.dispatch("REFRESH_ALL_DATA_SOURCES");
}

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
            execute: (child_env) => _refreshAndReinsertAllPivots(child_env),
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
    async reinsertTable(env, mode) {
        const pivot = env.model.getters.getPivot(this.props.pivotId);
        // Reload fresh data from Odoo before reading the table structure.
        // The previous implementation dispatched REFRESH_PIVOT *after* reading
        // stale data, so the re-inserted table always contained old values.
        await pivot.load({reload: true});
        const zone = env.model.getters.getSelectedZone();
        const table = pivot.getTableStructure().export();
        env.model.dispatch("INSERT_PIVOT_WITH_TABLE", {
            pivotId: this.props.pivotId,
            table,
            col: zone.left,
            row: zone.top,
            sheetId: env.model.getters.getActiveSheetId(),
            pivotMode: mode,
        });
    }
}

export class PivotPanelDisplay extends Component {
    setup() {
        this.dialog = useService("dialog");
        this.store = useLocalStore(PivotSidePanelStore, this.props.pivotId);
        this.pivotPanelRef = useRef("pivotPanel");
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
            resModel: this.store.definition.model,
            domain: this.domain,
            readonly: false,
            isDebugMode: Boolean(this.env.debug),
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
        return this.pivotPanelRef.el;
    }
    flipAxis() {
        const dimensions = {
            rows: this.store.definition.columns,
            columns: this.store.definition.rows,
        };
        this.updateDimensions(dimensions);
    }
}

PivotPanelDisplay.template = "spreadsheet_oca.PivotPanelDisplay";
PivotPanelDisplay.components = {
    DomainSelector,
    PivotTitleSectionInsertion,
    PivotLayoutConfiguratorWithAggregators,
};
PivotPanelDisplay.properties = {
    pivotId: String,
};

export class PivotPanel extends Component {
    get pivotId() {
        return this.props.pivotId;
    }
    get pivotType() {
        return this.env.model.getters.getPivotCoreDefinition(this.pivotId).type;
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
