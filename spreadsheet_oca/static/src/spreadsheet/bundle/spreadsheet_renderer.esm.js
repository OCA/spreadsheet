/** @odoo-module **/

import {Component} from "@odoo/owl";
import {DataSources} from "@spreadsheet/data_sources/data_sources";
import Dialog from "web.OwlDialog";
import {Field} from "@web/views/fields/field";
import {loadSpreadsheetDependencies} from "@spreadsheet/helpers/helpers";
import {migrate} from "@spreadsheet/o_spreadsheet/migration";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import {useService} from "@web/core/utils/hooks";
import {useSetupAction} from "@web/webclient/actions/action_hook";

const {Spreadsheet, Model} = spreadsheet;
const {useSubEnv, useState, onWillStart} = owl;
const uuidGenerator = new spreadsheet.helpers.UuidGenerator();

class SpreadsheetTransportService {
    constructor(orm, bus_service, model, res_id) {
        this.orm = orm;
        this.bus_service = bus_service;
        this.model = model;
        this.res_id = res_id;
        this.channel = "spreadsheet_oca;" + this.model + ";" + this.res_id;
        this.bus_service.addChannel(this.channel);
        this.bus_service.addEventListener(
            "notification",
            this.onNotification.bind(this)
        );
        this.listeners = [];
    }
    onNotification({detail: notifications}) {
        for (const {payload, type} of notifications) {
            if (
                type === "spreadsheet_oca" &&
                payload.res_model === this.model &&
                payload.res_id === this.res_id
            ) {
                // What shall we do if no callback is defined (empty until onNewMessage...) :/
                for (const {callback} of this.listeners) {
                    callback(payload);
                }
            }
        }
    }
    sendMessage(message) {
        this.orm.call(this.model, "send_spreadsheet_message", [[this.res_id], message]);
    }
    onNewMessage(id, callback) {
        this.listeners.push({id, callback});
    }
    leave(id) {
        this.listeners = this.listeners.filter((listener) => listener.id !== id);
    }
}

export class SpreadsheetRenderer extends Component {
    setup() {
        this.orm = useService("orm");
        this.bus_service = useService("bus_service");
        this.user = useService("user");
        const dataSources = new DataSources(this.orm);
        this.state = useState({
            dialogDisplayed: false,
            dialogTitle: "Spreadsheet",
            dialogContent: undefined,
        });
        this.confirmDialog = this.closeDialog;
        this.spreadsheet_model = new Model(
            migrate(this.props.record.spreadsheet_raw),
            {
                evalContext: {env: this.env, orm: this.orm},
                transportService: new SpreadsheetTransportService(
                    this.orm,
                    this.bus_service,
                    this.props.model,
                    this.props.res_id
                ),
                client: {
                    id: uuidGenerator.uuidv4(),
                    name: this.user.name,
                },
                mode: this.props.record.mode,
                dataSources,
            },
            this.props.record.revisions
        );
        useSubEnv({
            saveSpreadsheet: this.onSpreadsheetSaved.bind(this),
            editText: this.editText.bind(this),
            askConfirmation: this.askConfirmation.bind(this),
        });
        onWillStart(async () => {
            await loadSpreadsheetDependencies();
            await dataSources.waitForAllLoaded();
            await this.env.importData(this.spreadsheet_model);
        });
        useSetupAction({
            beforeLeave: () => this.onSpreadsheetSaved(),
        });
        dataSources.addEventListener("data-source-updated", () => {
            const sheetId = this.spreadsheet_model.getters.getActiveSheetId();
            this.spreadsheet_model.dispatch("EVALUATE_CELLS", {sheetId});
        });
    }
    closeDialog() {
        this.state.dialogDisplayed = false;
        this.state.dialogTitle = "Spreadsheet";
        this.state.dialogContent = undefined;
        this.state.dialogHideInputBox = false;
    }
    onSpreadsheetSaved() {
        const data = this.spreadsheet_model.exportData();
        this.env.saveRecord({spreadsheet_raw: data});
        this.spreadsheet_model.leaveSession();
    }
    editText(title, callback, options) {
        this.state.dialogContent = options.placeholder;
        this.state.dialogTitle = title;
        this.state.dialogDisplayed = true;
        this.confirmDialog = () => {
            callback(this.state.dialogContent);
            this.closeDialog();
        };
    }
    askConfirmation(content, confirm) {
        this.state.dialogContent = content;
        this.state.dialogDisplayed = true;
        this.state.dialogHideInputBox = true;
        this.confirmDialog = () => {
            confirm();
            this.closeDialog();
        };
    }
}

SpreadsheetRenderer.template = "spreadsheet_oca.SpreadsheetRenderer";
SpreadsheetRenderer.components = {
    Spreadsheet,
    Field,
    Dialog,
};
SpreadsheetRenderer.props = {
    record: Object,
    res_id: {type: Number, optional: true},
    model: String,
    importData: {type: Function, optional: true},
};
