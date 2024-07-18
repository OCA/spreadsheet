/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";
import {_lt, _t} from "web.core";

import {FilterValue} from "@spreadsheet/global_filters/components/filter_value/filter_value";
import {ModelFieldSelector} from "@web/core/model_field_selector/model_field_selector";
import {ModelSelector} from "@web/core/model_selector/model_selector";
import {RELATIVE_DATE_RANGE_TYPES} from "@spreadsheet/helpers/constants";
import {globalFiltersFieldMatchers} from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import {useService} from "@web/core/utils/hooks";

const {topbarMenuRegistry} = spreadsheet.registries;
const uuidGenerator = new spreadsheet.helpers.UuidGenerator();

topbarMenuRegistry.add("file", {name: _t("File"), sequence: 10});
topbarMenuRegistry.addChild("filters", ["file"], {
    name: _t("Filters"),
    sequence: 70,
    action: (env) => env.openSidePanel("FilterPanel", {}),
});
topbarMenuRegistry.addChild("save", ["file"], {
    name: _t("Save"),
    // Description: "Ctrl+S", // This is not working, so removing it from the view for now...
    sequence: 10,
    action: (env) => env.saveSpreadsheet(),
});
topbarMenuRegistry.addChild("download", ["file"], {
    name: _t("Download XLSX"),
    sequence: 20,
    action: (env) => env.downloadAsXLXS(),
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
        this.filterId = this.props.filter;
        this.orm = useService("orm");
        this.state = useState({
            label: this.props.filter.label,
            type: this.props.filter.type,
            defaultValue: this.props.filter.defaultValue,
            defaultsToCurrentPeriod: this.props.filter.defaultsToCurrentPeriod,
            rangeType: this.props.filter.rangeType || "year",
            modelName: {technical: this.props.filter.modelName, label: null},
            objects: {},
        });
        this.relativeDateRangeTypes = RELATIVE_DATE_RANGE_TYPES;
        onWillStart(this.willStart.bind(this));
    }
    async willStart() {
        if (this.state.modelName.technical !== undefined) {
            const modelLabel = await this.orm.call("ir.model", "display_name_for", [
                [this.state.modelName.technical],
            ]);
            this.state.modelName.label = modelLabel[0] && modelLabel[0].display_name;
        }
        var ModelFields = [];
        for (var [objectType, objectClass] of Object.entries(
            globalFiltersFieldMatchers
        )) {
            for (const objectId of objectClass.geIds()) {
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
            {type: "year", description: _t("Year")},
            {type: "quarter", description: _t("Quarter")},
            {type: "month", description: _t("Month")},
            {type: "relative", description: _t("Relative Period")},
        ];
    }
    get dateOffset() {
        return [
            {value: 0, name: ""},
            {value: -1, name: _lt("Previous")},
            {value: -2, name: _lt("Before Previous")},
            {value: 1, name: _lt("Next")},
            {value: 2, name: _lt("After next")},
        ];
    }
    onChangeFieldMatchOffset(object, ev) {
        this.state.objects[object.id].fieldMatch.offset = parseInt(ev.target.value, 10);
    }
    onModelSelected(ev) {
        this.state.modelName.technical = ev.technical;
        this.state.modelName.label = ev.label;
    }
    onDateRangeChange(ev) {
        this.state.rangeType = ev.target.value;
    }
    onSave() {
        const action = this.props.filter.id
            ? "EDIT_GLOBAL_FILTER"
            : "ADD_GLOBAL_FILTER";
        this.env.openSidePanel("FilterPanel", {});
        var filter = {
            id: this.props.filter.id || uuidGenerator.uuidv4(),
            type: this.state.type,
            label: this.state.label,
            defaultValue: this.state.defaultValue,
            rangeType: this.state.rangeType,
            defaultsToCurrentPeriod: this.state.defaultsToCurrentPeriod,
            modelName: this.state.modelName.technical,
        };
        var filterMatching = {};
        Object.values(this.state.objects).forEach((object) => {
            filterMatching[object.type] = filterMatching[object.type] || {};
            filterMatching[object.type][object.objectId] = {...object.fieldMatch};
        });
        this.env.model.dispatch(action, {id: filter.id, filter, ...filterMatching});

        this.env.openSidePanel("FilterPanel", {});
    }
    onCancel() {
        this.env.openSidePanel("FilterPanel", {});
    }
    onRemove() {
        if (this.props.filter.id) {
            this.env.model.dispatch("REMOVE_GLOBAL_FILTER", {id: this.props.filter.id});
        }
        this.env.openSidePanel("FilterPanel", {});
    }
    onFieldMatchUpdate(object, name) {
        this.state.objects[object.id].fieldMatch.chain = name;
    }
}

EditFilterPanel.template = "spreadsheet_oca.EditFilterPanel";
EditFilterPanel.components = {ModelSelector, ModelFieldSelector};

sidePanelRegistry.add("EditFilterPanel", {
    title: "Edit Filter",
    Body: EditFilterPanel,
});
