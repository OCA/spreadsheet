import * as spreadsheet from "@odoo/o-spreadsheet";

import {Component} from "@odoo/owl";
import {ImageFileStore} from "./image_file_store.esm";
import {OdooDataProvider} from "@spreadsheet/data_sources/odoo_data_provider";
import {SpreadsheetComponent} from "@spreadsheet/actions/spreadsheet_component";
import {_t} from "@web/core/l10n/translation";
import {loadSpreadsheetDependencies} from "@spreadsheet/assets_backend/helpers";
import {useService} from "@web/core/utils/hooks";
import {useSetupAction} from "@web/search/action_hook";
import {user} from "@web/core/user";
import {waitForDataLoaded} from "@spreadsheet/helpers/model";

const {Model, load} = spreadsheet;

const {useSubEnv, onWillStart} = owl;
const {useStoreProvider, ModelStore} = spreadsheet.stores;
const uuidGenerator = new spreadsheet.helpers.UuidGenerator();

class SpreadsheetTransportService {
    constructor(orm, bus_service, model, res_id) {
        this.orm = orm;
        this.bus_service = bus_service;
        this.model = model;
        this.res_id = res_id;
        this.channel = "spreadsheet_oca;" + this.model + ";" + this.res_id;
        this.bus_service.addChannel(this.channel);
        this.dialog = useService("dialog");
        this.bus_service.subscribe("notification", (payload) => {
            if (payload.id === this.res_id) {
                this._handleNotification(payload);
            }
        });
        this.listeners = [];
        this._listener = null;
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
    async sendMessage(message) {
        const isAccepted = await this.orm.call(this.model, "send_spreadsheet_message", [
            [this.res_id],
            message,
            this.accessToken,
        ]);
        if (isAccepted) {
            this._handleNotification(message);
        }
    }
    onNewMessage(id, callback) {
        this._listener = callback;
        for (const message of this.listeners) {
            callback(message);
        }
        this.listeners = [];
    }
    leave(id) {
        this.listeners = this.listeners.filter((listener) => listener.id !== id);
    }
    _handleNotification(payload) {
        if (!this._listener) {
            this.listeners.push(payload);
        } else {
            this._listener(payload);
        }
    }
}

export class SpreadsheetRenderer extends Component {
    createDefaultCurrency(currency) {
        if (!currency) {
            return undefined;
        }
        return {
            symbol: currency.symbol,
            position: currency.position,
            decimalPlaces: currency.decimal_places,
        };
    }
    getLocales() {
        const orm = useService("orm");
        return async () => {
            return orm.call("res.lang", "get_locales_for_spreadsheet", []);
        };
    }
    getCurrencies() {
        const orm = useService("orm");
        return async () => {
            const odooCurrencies = await orm.searchRead(
                "res.currency",
                [],
                ["symbol", "full_name", "position", "name", "decimal_places"],
                {
                    order: "active DESC, full_name ASC",
                    context: {active_test: false},
                }
            );
            return odooCurrencies.map((currency) => {
                return {
                    code: currency.name,
                    symbol: currency.symbol,
                    position: currency.position || "after",
                    name: currency.full_name || _t("Currency"),
                    decimalPlaces: currency.decimal_places || 2,
                };
            });
        };
    }
    setup() {
        this.orm = useService("orm");
        this.http = useService("http");
        this.bus_service = this.env.services.bus_service;
        this.ui = useService("ui");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notifications = useService("notification");
        const odooDataProvider = new OdooDataProvider(this.env);
        this.loadCurrencies = this.getCurrencies();
        this.loadLocales = this.getLocales();
        const defaultCurrency = this.props.record.default_currency;
        this.fileStore = new ImageFileStore(
            this.props.model,
            this.props.res_id,
            this.http,
            this.orm
        );
        this.stores = useStoreProvider();
        // The o-spreadsheet Model handles currency formatting internally
        this.spreadsheet_model = new Model(
            load(this.props.record.spreadsheet_raw),
            {
                custom: {env: this.env, orm: this.orm, odooDataProvider},
                defaultCurrency: this.createDefaultCurrency(defaultCurrency),
                external: {
                    loadCurrencies: this.loadCurrencies,
                    loadLocales: this.loadLocales,
                    fileStore: this.fileStore,
                },
                transportService: new SpreadsheetTransportService(
                    this.orm,
                    this.bus_service,
                    this.props.model,
                    this.props.res_id
                ),
                client: {
                    id: uuidGenerator.uuidv4(),
                    name: user.name,
                    userId: user.userId,
                },
                mode: this.props.record.mode,
            },
            this.props.record.revisions
        );
        useSubEnv({
            saveSpreadsheet: this.onSpreadsheetSaved.bind(this),
            downloadAsXLXS: this.downloadAsXLXS.bind(this),
        });
        onWillStart(async () => {
            await loadSpreadsheetDependencies();
            await waitForDataLoaded(this.spreadsheet_model);
            await this.env.importData(this.spreadsheet_model);
            this.spreadsheet_model.joinSession();
            this.stores.inject(ModelStore, this.spreadsheet_model);
        });
        useSetupAction({
            beforeLeave: this.onSpreadsheetSaved.bind(this),
        });
        odooDataProvider.addEventListener("data-source-updated", () => {
            const sheetId = this.spreadsheet_model.getters.getActiveSheetId();
            this.spreadsheet_model.dispatch("EVALUATE_CELLS", {sheetId});
        });
    }
    async onSpreadsheetSaved() {
        const data = this.spreadsheet_model.exportData();
        await this.env.saveRecord({spreadsheet_raw: data});
        await this.spreadsheet_model.leaveSession();
        this.spreadsheet_model.off("update", this);
    }
    async downloadAsXLXS() {
        this.ui.block();
        await waitForDataLoaded(this.spreadsheet_model);
        await this.action.doAction({
            type: "ir.actions.client",
            tag: "action_download_spreadsheet",
            params: {
                name: this.props.record.name,
                xlsxData: this.spreadsheet_model.exportXLSX(),
            },
        });
        this.ui.unblock();
    }
}

SpreadsheetRenderer.template = "spreadsheet_oca.SpreadsheetRenderer";
SpreadsheetRenderer.components = {SpreadsheetComponent};
SpreadsheetRenderer.props = {
    record: Object,
    res_id: Number,
    model: String,
    importData: Function,
};
