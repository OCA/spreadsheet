import * as spreadsheet from "@odoo/o-spreadsheet";
import {Component, onWillStart, useState} from "@odoo/owl";
import {Domain} from "@web/core/domain";
import {DomainSelector} from "@web/core/domain_selector/domain_selector";
import {DomainSelectorDialog} from "@web/core/domain_selector_dialog/domain_selector_dialog";
import {FilterValue} from "@spreadsheet/global_filters/components/filter_value/filter_value";
import {ModelFieldSelector} from "@web/core/model_field_selector/model_field_selector";
import {ModelSelector} from "@web/core/model_selector/model_selector";
import {MultiRecordSelector} from "@web/core/record_selectors/multi_record_selector";
import {RELATIVE_DATE_RANGE_TYPES} from "@spreadsheet/helpers/constants";
const {Checkbox} = spreadsheet.components;
import {user} from "@web/core/user";

import {_t} from "@web/core/l10n/translation";
import {globalFiltersFieldMatchers} from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";
import {useService} from "@web/core/utils/hooks";

const {topbarMenuRegistry} = spreadsheet.registries;
const uuidGenerator = new spreadsheet.helpers.UuidGenerator();

topbarMenuRegistry.add("file", {name: _t("File"), sequence: 10});
topbarMenuRegistry.addChild("filters", ["file"], {
    name: _t("Filters"),
    sequence: 70,
    execute: (env) => env.openSidePanel("FilterPanel", {}),
    icon: "o-spreadsheet-Icon.GLOBAL_FILTERS",
});
topbarMenuRegistry.addChild("save", ["file"], {
    name: _t("Save"),
    // Description: "Ctrl+S", // This is not working, so removing it from the view for now...
    sequence: 10,
    execute: (env) => env.saveSpreadsheet(),
    icon: "o-spreadsheet-Icon.DOWNLOAD",
});
topbarMenuRegistry.addChild("download", ["file"], {
    name: _t("Download XLSX"),
    sequence: 20,
    execute: (env) => env.downloadAsXLXS(),
    icon: "o-spreadsheet-Icon.EXPORT_XLSX",
});
topbarMenuRegistry.addChild("settings", ["file"], {
    name: _t("Settings"),
    sequence: 100,
    execute: (env) => env.openSidePanel("Settings"),
    icon: "o-spreadsheet-Icon.COG",
});

const {sidePanelRegistry} = spreadsheet.registries;

export class FilterPanel extends Component {
    onEditFilter(filter) {
        this.env.openSidePanel("EditFilterPanel", {filter});
    }
    onAddFilter(type) {
        this.env.openSidePanel("EditFilterPanel", {filter: {type: type}});
    }
}

FilterPanel.template = "spreadsheet_oca.FilterPanel";
FilterPanel.components = {
    FilterValue,
};

sidePanelRegistry.add("FilterPanel", {
    title: "Filters",
    Body: FilterPanel,
});

export class EditFilterPanel extends Component {
    setup() {
        this.filterId = this.props.filter.id;
        this.orm = useService("orm");
        this.nameService = useService("name");
        this.dialog = useService("dialog");
        this.state = useState({
            label: this.props.filter.label,
            type: this.props.filter.type,
            defaultValue: this.props.filter.defaultValue || [],
            defaultValueDisplayNames: this.props.filter.defaultValueDisplayNames || [],
            rangeType: this.props.filter.rangeType || "year",
            modelData: {technical: this.props.filter.modelName, label: null},
            objects: {},
            includeChildren: this.props.filter.includeChildren,
            domainOfAllowedValues: this.props.filter.domainOfAllowedValues,
            valuesRestricted: Boolean(this.props.filter.domainOfAllowedValues?.length),
        });
        this.relativeDateRangeTypes = RELATIVE_DATE_RANGE_TYPES;
        onWillStart(this.willStart.bind(this));
    }
    async willStart() {
        if (this.state.modelData.technical !== undefined) {
            const technicalName = this.state.modelData.technical;
            const modelLabel = await this.orm.call("ir.model", "display_name_for", [
                [technicalName],
            ]);
            this.state.modelData.label = modelLabel[0] && modelLabel[0].display_name;
            if (this.state.includeChildren) {
                this.state.modelData.hasParentRelation = true;
            } else {
                const hasParentRelation = await this.orm.call(
                    "ir.model",
                    "has_parent_relation",
                    [technicalName]
                );
                this.state.modelData.hasParentRelation = hasParentRelation;
            }
        }
        var ModelFields = [];
        for (var [objectType, objectClass] of Object.entries(
            globalFiltersFieldMatchers
        )) {
            for (const objectId of objectClass.getIds()) {
                var fields = objectClass.getFields(objectId);
                this.state.objects[objectType + "_" + objectId] = {
                    id: objectType + "_" + objectId,
                    objectId: objectId,
                    name: objectClass.getDisplayName(objectId),
                    tag: await objectClass.getTag(objectId),
                    fieldMatch:
                        objectClass.getFieldMatching(objectId, this.props.filter.id) ||
                        {},
                    fields: fields,
                    type: objectType,
                    model: objectClass.getModel(objectId),
                };
                ModelFields.push(fields);
            }
        }
        this.models = [
            ...new Set(
                ModelFields.map((field_items) => Object.values(field_items))
                    .flat()
                    .filter((field) => field.relation)
                    .map((field) => field.relation)
            ),
        ];
    }
    get dateRangeTypes() {
        return [
            {type: "fixedPeriod", description: _t("Month / Quarter")},
            {type: "relative", description: _t("Relative Period")},
            {type: "from_to", description: _t("From / To")},
        ];
    }
    get dateOffset() {
        return [
            {value: 0, name: ""},
            {value: -1, name: _t("Previous")},
            {value: -2, name: _t("Before Previous")},
            {value: 1, name: _t("Next")},
            {value: 2, name: _t("After next")},
        ];
    }
    onChangeFieldMatchOffset(object, ev) {
        this.state.objects[object.id].fieldMatch.offset = parseInt(ev.target.value, 10);
    }
    async onModelSelected(ev) {
        this.state.modelData.technical = ev.technical;
        this.state.modelData.label = ev.label;
        this.state.modelData.hasParentRelation = await this.orm.call(
            "ir.model",
            "has_parent_relation",
            [ev.technical]
        );
        this.state.domainOfAllowedValues = [];
    }
    async onRecordsSelected(resIds) {
        const defaultValueDisplayNames = await this.nameService.loadDisplayNames(
            this.state.modelData.technical,
            resIds
        );
        this.state.defaultValue = resIds;
        this.state.defaultValueDisplayNames = Object.values(defaultValueDisplayNames);
    }
    onUpdateDomain(domain) {
        this.state.domainOfAllowedValues = domain;
    }
    getCorrectDomain() {
        const domain = this.state.domainOfAllowedValues;
        if (domain) {
            return new Domain(domain).toList(user.context);
        }
        return [];
    }
    changeDomainRestriction(value) {
        this.state.valuesRestricted = value;
        this.state.domainOfAllowedValues = [];
    }
    editDomain() {
        this.dialog.add(DomainSelectorDialog, {
            resModel: this.state.modelData.technical,
            domain: this.getCorrectDomain(),
            readonly: false,
            isDebugMode: Boolean(this.env.debug),
            onConfirm: this.onUpdateDomain.bind(this),
        });
    }
    onDateRangeChange(ev) {
        this.state.rangeType = ev.target.value;
        this.state.defaultValue = undefined;
    }
    onSave() {
        const action = this.props.filter.id
            ? "EDIT_GLOBAL_FILTER"
            : "ADD_GLOBAL_FILTER";

        const filter = {
            id: this.props.filter.id || uuidGenerator.uuidv4(),
            type: this.state.type,
            label: this.state.label || "",
            defaultValue: this.state.defaultValue,
            defaultValueDisplayNames: this.state.defaultValueDisplayNames,
            rangeType: this.state.rangeType,
            modelName: this.state.modelData.technical,
            includeChildren: this.state.includeChildren,
            domainOfAllowedValues: this.state.domainOfAllowedValues,
        };
        const filterMatching = {};
        Object.values(this.state.objects).forEach((object) => {
            filterMatching[object.type] = filterMatching[object.type] || {};
            const fieldMatch = object.fieldMatch ? {...object.fieldMatch} : {};
            filterMatching[object.type][object.objectId] = fieldMatch;
        });
        this.env.model.dispatch(action, {
            filter,
            ...filterMatching,
        });
        this.env.openSidePanel("FilterPanel", {});
    }
    onCancel() {
        this.env.openSidePanel("FilterPanel", {});
    }
    onRemove() {
        if (this.props.filter.id) {
            this.env.model.dispatch("REMOVE_GLOBAL_FILTER", {
                id: this.props.filter.id,
            });
        }
        this.env.openSidePanel("FilterPanel", {});
    }
    onFieldMatchUpdate(object, path, fieldInfo) {
        if (!path) {
            // Clear the field match if no path selected
            this.state.objects[object.id].fieldMatch = {};
            return;
        }
        // Extract field definition from fieldInfo (V18> structure)
        const fieldDef =
            fieldInfo && fieldInfo.fieldDef ? fieldInfo.fieldDef : fieldInfo;
        this.state.objects[object.id].fieldMatch = {
            chain: path,
            type: fieldDef?.type || "",
        };
    }
    toggleDateDefaultValue(ev) {
        this.state.defaultValue = ev.target.checked ? "this_month" : undefined;
    }
    getModelField(fieldMatch) {
        if (!fieldMatch || !fieldMatch.chain) {
            return "";
        }
        return fieldMatch.chain;
    }
    filterModelFieldSelectorField(field, path, coModel) {
        if (!field.searchable) {
            return false;
        }

        // TODO: Define allowed field types based on filter type
        const ALLOWED_FIELD_TYPES = [
            "char",
            "text",
            "selection",
            "many2one",
            "date",
            "datetime",
        ];

        if (field.name === "id" && this.state.type === "relation") {
            const paths = path.split(".");
            const lastField = paths.at(-2);
            if (!lastField || (lastField.relation && lastField.relation === coModel)) {
                return true;
            }
            return false;
        }
        return ALLOWED_FIELD_TYPES.includes(field.type) || Boolean(field.relation);
    }
}

EditFilterPanel.template = "spreadsheet_oca.EditFilterPanel";
EditFilterPanel.components = {
    Checkbox,
    DomainSelector,
    ModelSelector,
    ModelFieldSelector,
    MultiRecordSelector,
};

sidePanelRegistry.add("EditFilterPanel", {
    title: "Edit Filter",
    Body: EditFilterPanel,
});
