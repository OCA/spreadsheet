import {onWillStart, useState, useSubEnv} from "@odoo/owl";
import {ActionSpreadsheetOca} from "@spreadsheet_oca/spreadsheet/bundle/spreadsheet_action.esm";
import {WarningDialog} from "@web/core/errors/error_dialogs";
import {_t} from "@web/core/l10n/translation";
import {collectFieldLinks} from "./collect_field_links.esm";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(ActionSpreadsheetOca.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.linkModelHolder = {model: null};
        this.linkState = useState({writable: false, recordName: ""});
        useSubEnv({linkModelHolder: this.linkModelHolder, linkState: this.linkState});
        onWillStart(async () => {
            const context = await this.orm.call(
                "spreadsheet.spreadsheet",
                "get_linking_context",
                [[this.spreadsheetId]]
            );
            this.linkState.writable = context.writable;
            this.linkState.recordName = context.recordName || "";
        });
    },

    get writeToRecordLabel() {
        return this.linkState.recordName
            ? _t("Write to %s", this.linkState.recordName)
            : _t("Write to record");
    },

    async onWriteToRecord() {
        const model = this.linkModelHolder.model;
        if (!model) {
            return;
        }
        const {mappings, errors} = collectFieldLinks(model);
        if (errors.length) {
            this.dialog.add(WarningDialog, {
                title: _t("Unable to write to the record"),
                message: errors.join("\n\n"),
            });
            return;
        }
        const result = await this.orm.call(
            "spreadsheet.spreadsheet",
            "write_field_mappings",
            [
                [this.spreadsheetId],
                mappings.map(({chain, selectors, value}) => ({
                    chain,
                    selectors,
                    value,
                })),
            ]
        );
        const parts = [];
        if (result.updated) {
            parts.push(_t("%s line(s) updated", result.updated));
        }
        if (result.created) {
            parts.push(_t("%s line(s) created", result.created));
        }
        this.notification.add(parts.join(", ") || _t("No values to write."), {
            type: parts.length ? "success" : "info",
        });
        this.action.doAction({type: "ir.actions.act_window_close"});
    },
});
