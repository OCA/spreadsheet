/** @odoo-module **/

import * as spreadsheet from "@odoo/o-spreadsheet";
import { Component } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { DataSources } from "@spreadsheet/data_sources/data_sources";
import { Dialog } from "@web/core/dialog/dialog";
import { Field } from "@web/views/fields/field";
import { _t } from "@web/core/l10n/translation";
import { loadSpreadsheetDependencies } from "@spreadsheet/assets_backend/helpers";
import { migrate } from "@spreadsheet/o_spreadsheet/migration";
import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "@web/webclient/actions/action_hook";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { createDefaultCurrencyFormat } from "@spreadsheet/currency/helpers";

const { Spreadsheet, Model } = spreadsheet;
const { useSubEnv, onWillStart } = owl;
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
  onNotification({ detail: notifications }) {
    for (const { payload, type } of notifications) {
      if (
        type === "spreadsheet_oca" &&
        payload.res_model === this.model &&
        payload.res_id === this.res_id
      ) {
        // What shall we do if no callback is defined (empty until onNewMessage...) :/
        for (const { callback } of this.listeners) {
          callback(payload);
        }
      }
    }
  }
  sendMessage(message) {
    this.orm.call(this.model, "send_spreadsheet_message", [
      [this.res_id],
      message,
    ]);
  }
  onNewMessage(id, callback) {
    this.listeners.push({ id, callback });
  }
  leave(id) {
    this.listeners = this.listeners.filter((listener) => listener.id !== id);
  }
}

export class SpreadsheetRenderer extends Component {
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
          context: { active_test: false },
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
    this.bus_service = this.env.services.bus_service;
    this.user = useService("user");
    this.ui = useService("ui");
    this.action = useService("action");
    this.dialog = useService("dialog");
    const dataSources = new DataSources(this.env);
    this.confirmDialog = this.closeDialog;
    this.loadCurrencies = this.getCurrencies();
    this.loadLocales = this.getLocales();
    const defaultCurrency = this.props.record.default_currency;
    const defaultCurrencyFormat = defaultCurrency
      ? createDefaultCurrencyFormat(defaultCurrency)
      : undefined;
    this.spreadsheet_model = new Model(
      migrate(this.props.record.spreadsheet_raw),
      {
        custom: { env: this.env, orm: this.orm, dataSources },
        defaultCurrencyFormat,
        external: {
          loadCurrencies: this.loadCurrencies,
          loadLocales: this.loadLocales,
        },
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
      },
      this.props.record.revisions
    );
    useSubEnv({
      saveSpreadsheet: this.onSpreadsheetSaved.bind(this),
      askConfirmation: this.askConfirmation.bind(this),
      downloadAsXLXS: this.downloadAsXLXS.bind(this),
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
      this.spreadsheet_model.dispatch("EVALUATE_CELLS", { sheetId });
    });
  }
  onSpreadsheetSaved() {
    const data = this.spreadsheet_model.exportData();
    this.env.saveRecord({ spreadsheet_raw: data });
    this.spreadsheet_model.leaveSession();
  }
  askConfirmation(content, confirm) {
    this.dialog.add(ConfirmationDialog, {
      title: _t("Odoo Spreadsheet"),
      body: content,
      confirm,
      confirmLabel: _t("Confirm"),
    });
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
SpreadsheetRenderer.components = {
  Spreadsheet,
  Field,
  Dialog,
};
SpreadsheetRenderer.props = {
  record: Object,
  res_id: { type: Number, optional: true },
  model: String,
  importData: { type: Function, optional: true },
};
