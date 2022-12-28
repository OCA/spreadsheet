/** @odoo-module **/

import {loadSpreadsheetAction} from "@spreadsheet/assets_backend/spreadsheet_action_loader";
import {registry} from "@web/core/registry";

const actionRegistry = registry.category("actions");

const loadSpreadsheetActionOca = async (env, context) => {
    await loadSpreadsheetAction(
        env,
        "action_spreadsheet_oca",
        loadSpreadsheetActionOca
    );
    return {
        ...context,
        target: "current",
        tag: "action_spreadsheet_oca",
        type: "ir.actions.client",
    };
};
actionRegistry.add("action_spreadsheet_oca", loadSpreadsheetActionOca);
