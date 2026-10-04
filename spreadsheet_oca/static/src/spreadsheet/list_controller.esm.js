import {INSERT_LIST_EVENT} from "./list_cog_menu.esm";
import {ListController} from "@web/views/list/list_controller";
import {evaluateBooleanExpr} from "@web/core/py_js/py";
import {omit} from "@web/core/utils/objects";
import {patch} from "@web/core/utils/patch";
import {useBus} from "@web/core/utils/hooks";
import {user} from "@web/core/user";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        useBus(this.env.searchModel, INSERT_LIST_EVENT, () =>
            this.onSpreadsheetButtonClicked()
        );
    },
    onSpreadsheetButtonClicked() {
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
                            domain: this.env.searchModel.domainString,
                            orderBy: model.orderBy,
                            context: omit(
                                model.context || {},
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
        return this.props.archInfo.columns
            .filter(
                (col) =>
                    col.type === "field" &&
                    fields[col.name] &&
                    col.widget !== "handle" &&
                    !fields[col.name].relatedPropertyField &&
                    !evaluateBooleanExpr(col.column_invisible, this.props.context) &&
                    (!col.optional || this.optionalActiveFields[col.name]) &&
                    // We want to avoid binary or json fields
                    !["binary", "json"].includes(fields[col.name].type)
            )
            .map((col) => ({name: col.name, type: fields[col.name].type}));
    },
});
