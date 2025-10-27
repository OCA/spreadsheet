import * as spreadsheet from "@odoo/o-spreadsheet";
import {useState, useSubEnv} from "@odoo/owl";
import {SpreadsheetRenderer} from "@spreadsheet_oca/spreadsheet/bundle/spreadsheet_renderer.esm";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
const {topbarMenuRegistry} = spreadsheet.registries;
import {user} from "@web/core/user";

topbarMenuRegistry.addChild("add_to_dashboard", ["file"], {
    name: _t("Add to dashboard"),
    sequence: 120,
    execute: (env) => env.addToDashboard(),
    isVisible: (env) => env.canAddToDashboard?.(),
    icon: "o-spreadsheet-Icon.INSERT_CHART",
});

patch(SpreadsheetRenderer.prototype, {
    setup() {
        super.setup();
        this.state = useState({canAddToDashboard: false});
        this._checkDashboardPermission();
        useSubEnv({
            addToDashboard: this._addToDashboard.bind(this),
            canAddToDashboard: () => this.state.canAddToDashboard,
        });
    },
    async _checkDashboardPermission() {
        const result =
            (await user.hasGroup("base.group_system")) ||
            (await user.hasGroup("spreadsheet_dashboard.group_dashboard_manager"));
        this.state.canAddToDashboard = result;
    },
    async _addToDashboard() {
        const record = this.props.record;
        const resId = this.props.res_id;
        const name = record.name;
        this.onSpreadsheetSaved();
        this.env.services.action.doAction(
            {
                name: _t("Add to dashboard"),
                type: "ir.actions.act_window",
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                res_model: "spreadsheet.to.dashboard",
            },
            {
                additionalContext: {
                    default_spreadsheet_id: resId,
                    default_name: name,
                },
            }
        );
    },
});
