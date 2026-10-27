import * as spreadsheet from "@odoo/o-spreadsheet";
import {
    Component,
    onWillStart,
    onWillUpdateProps,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import {Domain} from "@web/core/domain";
import {DomainSelector} from "@web/core/domain_selector/domain_selector";
import {DomainSelectorDialog} from "@web/core/domain_selector_dialog/domain_selector_dialog";
import {ModelFieldSelector} from "@web/core/model_field_selector/model_field_selector";
import {ModelFieldSelectorPopover} from "@web/core/model_field_selector/model_field_selector_popover";
import {ODOO_AGGREGATORS} from "@spreadsheet/pivot/pivot_helpers";
import {_t} from "@web/core/l10n/translation";
import {formatDate} from "@web/core/l10n/dates";
import {useService} from "@web/core/utils/hooks";

const {DateTime} = luxon;
const {AddDimensionButton, PivotTitleSection, PivotLayoutConfigurator} =
    spreadsheet.components;
const {useLocalStore, PivotSidePanelStore} = spreadsheet.stores;
const {sidePanelRegistry, topbarMenuRegistry, pivotSidePanelRegistry, pivotRegistry} =
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

/**
 * Field selector popover that only follows many2one relations, the only ones
 * the ORM accepts in a read_group path (e.g. "company_id.country_id").
 */
class PivotFieldSelectorPopover extends ModelFieldSelectorPopover {
    canFollowRelationFor(fieldDef) {
        return fieldDef.type === "many2one" && fieldDef.groupable;
    }
}

/**
 * "Add" button of the pivot rows/columns. It replaces the flat field list
 * of o-spreadsheet by the Odoo field selector so related fields can be
 * picked as dimensions (e.g. "Company > Country").
 */
export class RelationalAddDimensionButton extends AddDimensionButton {
    get resModel() {
        return this.env.pivotResModel;
    }
    /**
     * @param {Object} field
     * @param {String} path path of the page holding the field, empty on the
     * root model
     */
    filterField(field, path) {
        const isFollowable = field.type === "many2one" && field.groupable;
        if (!path) {
            const unusedFields = new Set(this.props.fields.map((f) => f.name));
            return unusedFields.has(field.name) || isFollowable;
        }
        // X2many fields cannot be part of a read_group path
        return (
            !["one2many", "many2many"].includes(field.type) &&
            (isFollowable || pivotRegistry.get("ODOO").isGroupable(field))
        );
    }
    onPathSelected(path, field) {
        // The popover also calls update when it opens a page: only react to
        // an actual field selection.
        if (!field) {
            return;
        }
        this.props.onFieldPicked(path);
    }
    closePopover() {
        this.popover.isOpen = false;
    }
}
RelationalAddDimensionButton.template = "spreadsheet_oca.RelationalAddDimensionButton";
RelationalAddDimensionButton.components = {
    ...AddDimensionButton.components,
    PivotFieldSelectorPopover,
};

export class PivotLayoutConfiguratorWithAggregators extends PivotLayoutConfigurator {
    setup() {
        super.setup();
        this.AGGREGATORS = ODOO_AGGREGATORS;
        useSubEnv({
            pivotResModel: this.env.model.getters.getPivotCoreDefinition(
                this.props.pivotId
            ).model,
        });
    }
    /**
     * A followed many2one stays pickable in the field selector even when it
     * is already a dimension, so ignore duplicates here.
     */
    isUsedDimension(fieldName) {
        const {columns, rows} = this.props.definition;
        return [...columns, ...rows].some((d) => d.fieldName === fieldName);
    }
    addColumnDimension(fieldName) {
        if (!this.isUsedDimension(fieldName)) {
            super.addColumnDimension(fieldName);
        }
    }
    addRowDimension(fieldName) {
        if (!this.isUsedDimension(fieldName)) {
            super.addRowDimension(fieldName);
        }
    }
}
PivotLayoutConfiguratorWithAggregators.template =
    "spreadsheet_oca.PivotLayoutConfigurator";
PivotLayoutConfiguratorWithAggregators.components = {
    ...PivotLayoutConfigurator.components,
    RelationalAddDimensionButton,
};

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
PivotPanelDisplay.props = {
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
PivotPanel.props = {
    pivotId: {type: String, optional: true},
    "*": true,
};
PivotPanel.components = {
    PivotPanelDisplay,
};

pivotSidePanelRegistry.add("ODOO", {
    editor: PivotPanel,
});

// Field types that cannot be displayed in a list cell
const UNSUPPORTED_LIST_FIELD_TYPES = [
    "binary",
    "json",
    "properties",
    "properties_definition",
];

export class ListPanelDisplay extends Component {
    setup() {
        this.state = useState({listRows: undefined, newColumnPath: ""});
        this.dialog = useService("dialog");
        this.fieldService = useService("field");
        // Labels of the column paths, keyed by "model:path"
        this.columnLabels = {};
        onWillStart(() => this.modelData(this.props));
        onWillUpdateProps((nextProps) => this.modelData(nextProps));
    }
    async modelData(props) {
        this.ListDataSource = await this.env.model.getters.getAsyncListDataSource(
            props.listId
        );
        this.modelLabel = await this.ListDataSource.getModelLabel();
        await this.loadColumnLabels(props.listDefinition);
    }
    /**
     * Compute a readable label ("Company > Name") for every column path.
     * Labels are cached, so only new paths trigger a field lookup.
     */
    async loadColumnLabels({model, columns}) {
        const missing = (columns || []).filter(
            (path) => !(`${model}:${path}` in this.columnLabels)
        );
        await Promise.all(
            missing.map(async (path) => {
                const {isInvalid, displayNames} =
                    await this.fieldService.loadPathDescription(model, path);
                this.columnLabels[`${model}:${path}`] = {
                    label: isInvalid ? path : displayNames.join(" > "),
                    isInvalid,
                };
            })
        );
    }
    get columns() {
        const {model, columns} = this.props.listDefinition;
        return (columns || []).map((path) => ({
            path,
            ...(this.columnLabels[`${model}:${path}`] || {label: path}),
        }));
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
    /**
     * Hide the fields that cannot be shown in a cell. Relational fields stay
     * visible so the user can follow them (e.g. company_id > name).
     */
    filterColumnField(field) {
        return !UNSUPPORTED_LIST_FIELD_TYPES.includes(field.type);
    }
    onNewColumnPathUpdate(path) {
        this.state.newColumnPath = path || "";
    }
    addColumn() {
        const path = this.state.newColumnPath;
        if (!path || this.props.listDefinition.columns.includes(path)) {
            return;
        }
        this.updateColumns([...this.props.listDefinition.columns, path]);
        this.state.newColumnPath = "";
    }
    removeColumn(index) {
        const columns = [...this.props.listDefinition.columns];
        columns.splice(index, 1);
        this.updateColumns(columns);
    }
    moveColumn(index, delta) {
        const columns = [...this.props.listDefinition.columns];
        const target = index + delta;
        if (target < 0 || target >= columns.length) {
            return;
        }
        [columns[index], columns[target]] = [columns[target], columns[index]];
        this.updateColumns(columns);
    }
    updateColumns(columns) {
        const list = JSON.parse(
            JSON.stringify(
                this.env.model.getters.getListModelDefinition(this.props.listId)
            )
        );
        list.metaData.columns = columns;
        this.env.model.dispatch("UPDATE_ODOO_LIST", {
            listId: this.props.listId,
            list,
        });
    }
    /**
     * Resolve the type of every column, following relations when the column
     * is a path like "company_id.name". Related columns get an explicit
     * header so it is clear which record the value comes from.
     */
    async getInsertColumns(list) {
        return Promise.all(
            list.columns.map(async (name) => {
                const {isInvalid, names, modelsInfo} = await this.fieldService.loadPath(
                    list.model,
                    name
                );
                if (isInvalid) {
                    return {name, type: "char"};
                }
                const field = modelsInfo.at(-1).fieldDefs[names.at(-1)];
                const column = {name, type: field.type};
                if (names.length > 1) {
                    // Escape quotes: the label ends up inside a formula string
                    column.string = this.columnLabels[
                        `${list.model}:${name}`
                    ]?.label.replaceAll('"', '\\"');
                }
                return column;
            })
        );
    }
    async insertList() {
        const listId = this.props.listId;
        const zone = this.env.model.getters.getSelectedZone();
        const dataSource = await this.env.model.getters.getAsyncListDataSource(listId);
        const totalRows = parseInt(this.state.listRows, 10) || dataSource.maxPosition;
        const list = this.env.model.getters.getListDefinition(listId);
        const sheetId = this.env.model.getters.getActiveSheetId();
        await this.loadColumnLabels(list);
        const columns = await this.getInsertColumns(list);
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
    ModelFieldSelector,
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
ListPanel.props = {
    listId: {type: String, optional: true},
    "*": true,
};
ListPanel.components = {
    ListPanelDisplay,
};

sidePanelRegistry.add("ListPanel", {
    title: "List information",
    Body: ListPanel,
});
