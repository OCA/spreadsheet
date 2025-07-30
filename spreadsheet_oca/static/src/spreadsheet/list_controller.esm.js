/** @odoo-module **/

import {ListController} from "@web/views/list/list_controller";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
import {user} from "@web/core/user";
import {omit} from "@web/core/utils/objects";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
        this.orm = useService("orm");
    },

    onClickAddToSpreadsheet() {
        const model = this.model.root;
        this.actionService.doAction(
            "spreadsheet_oca.spreadsheet_spreadsheet_import_act_window",
            {
                additionalContext: {
                    default_name: this.env.config.getDisplayName(),
                    default_datasource_name: this.env.config.getDisplayName(),
                    default_can_be_dynamic: true,
                    default_dynamic: true,
                    default_is_tree: true,
                    default_number_of_rows: Math.min(model.count, model.limit),
                    default_import_data: {
                        mode: "list",
                        metaData: {
                            model: model.resModel,
                            domain: model.domain,
                            orderBy: model.orderBy,
                            context: omit(
                                model.searchParams?.context || model.context || {},
                                ...Object.keys(user.context)
                            ),
                            columns: this.getSpreadsheetColumns(),
                            fields: model.fields,
                            name: this.env.config.getDisplayName(),
                        },
                    },
                },
            }
        );
    },

    getSpreadsheetColumns() {
        const fields = this.model.root.fields;

        const renderer = this.model.root.config?.renderer;
        if (renderer && renderer.columns) {
            return renderer.columns
                .filter(
                    (col) =>
                        col.type === "field" &&
                        fields[col.name] &&
                        !["binary", "json"].includes(fields[col.name].type)
                )
                .map((col) => ({name: col.name, type: fields[col.name].type}));
        }

        const state = this.model.root.data;
        if (state && state.length > 0 && state[0].data) {
            const dataColumns = Object.keys(state[0].data).filter(
                (fieldName) =>
                    fields[fieldName] &&
                    !["binary", "json"].includes(fields[fieldName].type)
            );
            return dataColumns.map((col) => ({name: col, type: fields[col].type}));
        }

        const fieldNames = this.model.root.fieldNames || Object.keys(fields);
        return fieldNames
            .filter(
                (fieldName) =>
                    fields[fieldName] &&
                    !["binary", "json", "one2many", "many2many"].includes(
                        fields[fieldName].type
                    )
            )
            .map((fieldName) => ({name: fieldName, type: fields[fieldName].type}));
    },
});
