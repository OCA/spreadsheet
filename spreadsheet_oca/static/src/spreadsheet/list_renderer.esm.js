import {useBus, useService} from "@web/core/utils/hooks";

import {HandleField} from "@web/views/fields/handle/handle_field";
import {ListRenderer} from "@web/views/list/list_renderer";
import {omit} from "@web/core/utils/objects";
import {patch} from "@web/core/utils/patch";
import {user} from "@web/core/user";

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
        useBus(
            this.env.bus,
            "addListOnSpreadsheet",
            this.onAddListOnSpreadsheet.bind(this)
        );
    },
    onAddListOnSpreadsheet() {
        const model = this.env.model.root;
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
                                model.searchParams?.context || {},
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
        const fields = this.env.model.root.fields;
        return this.columns
            .filter(
                (col) =>
                    col.type === "field" &&
                    col.field.component !== HandleField &&
                    !col.relatedPropertyField &&
                    !["binary", "json"].includes(fields[col.name].type)
                // We want to avoid binary or json fields
            )
            .map((col) => ({name: col.name, type: fields[col.name].type}));
    },
});
