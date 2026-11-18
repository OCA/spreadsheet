import {EvaluationError} from "@odoo/o-spreadsheet";
import {OdooUIPlugin} from "@spreadsheet/plugins";

export class MisBuilderPlugin extends OdooUIPlugin {
    static getters = ["getMisKpi"];

    constructor(config) {
        super(config);
        this._serverData = config.custom.odooDataProvider?.serverData;
    }

    get serverData() {
        if (!this._serverData) {
            throw new Error(
                "'serverData' is not defined, please make sure a 'OdooDataProvider' instance is provided to the model."
            );
        }
        return this._serverData;
    }

    /**
     * Value and format of a KPI of a MIS report template over a period.
     * Calls are batched: all the cells evaluated in the same tick are sent
     * in one request, and the server evaluates each report once per period.
     *
     * @param {Object} args
     * @param {Number} args.report_id
     * @param {String} args.kpi
     * @param {String} args.date_from
     * @param {String} args.date_to
     * @param {Number[]} args.company_ids
     * @param {Boolean} args.include_unposted
     * @param {String} args.subkpi
     * @returns {{value: Number|String|Boolean, format: String|Boolean}}
     */
    getMisKpi(args) {
        const result = this.serverData.batch.get(
            "mis.report",
            "spreadsheet_fetch_kpi",
            args
        );
        if (result.error) {
            throw new EvaluationError(result.error);
        }
        return result;
    }
}
