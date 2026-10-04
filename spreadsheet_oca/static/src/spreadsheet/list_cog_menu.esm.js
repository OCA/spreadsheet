import {Component} from "@odoo/owl";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {STATIC_ACTIONS_GROUP_NUMBER} from "@web/search/action_menus/action_menus";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

export const INSERT_LIST_EVENT = "spreadsheet_oca:insert-list";

/**
 * Cog menu entry of list views to add the current list to a spreadsheet.
 * The list controller builds the import data, as it knows the visible columns.
 */
export class SpreadsheetInsertListCogMenu extends Component {
    static template = "spreadsheet_oca.SpreadsheetInsertListCogMenu";
    static components = {DropdownItem};

    onSelected() {
        this.env.searchModel.trigger(INSERT_LIST_EVENT);
    }
}

registry.category("cogMenu").add(
    "spreadsheet-oca-insert-list",
    {
        Component: SpreadsheetInsertListCogMenu,
        groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
        isDisplayed: ({config}) => {
            const ui = useService("ui");
            return (
                !ui.isSmall &&
                config.actionType === "ir.actions.act_window" &&
                config.viewType === "list"
            );
        },
    },
    {sequence: 20}
);
