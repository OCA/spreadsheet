import {Component, onWillStart, useState} from "@odoo/owl";
import {ModelSelector} from "@web/core/model_selector/model_selector";
import {RecordSelector} from "@web/core/record_selectors/record_selector";
import {components} from "@odoo/o-spreadsheet";
import {useService} from "@web/core/utils/hooks";

const {Section} = components;

export class ManageLinkedRecordSidePanel extends Component {
    static template = "spreadsheet_field_linking.ManageLinkedRecordPanel";
    static components = {ModelSelector, RecordSelector, Section};
    static props = {onCloseSidePanel: Function};

    setup() {
        this.orm = useService("orm");
        this.models = [];
        this.linked = useState(this._snapshot());
        this.state = useState({
            model: this.linked.model || "",
            modelLabel: "",
            resId: this.linked.resId || false,
        });
        onWillStart(async () => {
            this.models = await this.orm.call(
                "spreadsheet.spreadsheet",
                "get_linkable_models",
                []
            );
            await this._loadModelLabel();
        });
    }

    _snapshot() {
        const context = this.env.model.getters.getFieldLinkContext();
        return {
            isLinkable: context.isLinkable,
            model: context.model,
            resId: context.resId,
            recordName: context.recordName,
            spreadsheetId: context.spreadsheetId,
        };
    }

    async _loadModelLabel() {
        if (!this.state.model) {
            this.state.modelLabel = "";
            return;
        }
        const [info] = await this.orm.call("ir.model", "display_name_for", [
            [this.state.model],
        ]);
        this.state.modelLabel = info?.display_name || this.state.model;
    }

    get context() {
        return this.linked;
    }

    get canApply() {
        return Boolean(this.state.model && this.state.resId);
    }

    async onModelSelected(model) {
        this.state.model = model.technical;
        this.state.modelLabel = model.label;
        this.state.resId = false;
    }

    onRecordSelected(resId) {
        this.state.resId = resId || false;
    }

    async _setTarget(model, resId) {
        const context = await this.orm.call(
            "spreadsheet.spreadsheet",
            "set_link_target",
            [[this.linked.spreadsheetId], model, resId]
        );
        Object.assign(this.env.model.getters.getFieldLinkContext(), context);
        if (this.env.linkState) {
            this.env.linkState.writable = context.writable;
            this.env.linkState.recordName = context.recordName || "";
        }
        Object.assign(this.linked, this._snapshot());
        this.state.model = this.linked.model || "";
        this.state.resId = this.linked.resId || false;
        await this._loadModelLabel();
    }

    async onApply() {
        if (this.canApply) {
            await this._setTarget(this.state.model, this.state.resId);
        }
    }

    async onUnlink() {
        await this._setTarget(false, false);
    }
}
