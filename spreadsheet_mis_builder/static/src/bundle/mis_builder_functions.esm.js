import * as spreadsheet from "@odoo/o-spreadsheet";
import {EvaluationError} from "@odoo/o-spreadsheet";
import {MisBuilderPlugin} from "./mis_builder_plugin.esm";
import {_t} from "@web/core/l10n/translation";

const {functionRegistry, featurePluginRegistry} = spreadsheet.registries;
const {arg, toBoolean, toJsDate, toNumber, toString} = spreadsheet.helpers;

const QUARTER_REGEXP = /^q([1-4])\/(\d{4})$/i;
const MONTH_REGEXP = /^0?([1-9]|1[0-2])\/(\d{4})$/;
const YEAR_REGEXP = /^(\d{4})$/;

function isEmpty(data) {
    return data === undefined || data.value === null || data.value === "";
}

function serverDate(year, month, day) {
    const pad = (number) => String(number).padStart(2, "0");
    return `${year}-${pad(month)}-${pad(day)}`;
}

function jsDateToServer(date) {
    return serverDate(date.getFullYear(), date.getMonth() + 1, date.getDate());
}

function lastDayOfMonth(year, month) {
    return new Date(year, month, 0).getDate();
}

/**
 * Convert the period arguments of MIS.KPI to server dates.
 *
 * @param {Object} dateFrom start date, or a period ("2026", "Q1/2026",
 *      "03/2026") when dateTo is empty
 * @param {Object} dateTo end date
 * @param {Object} locale
 * @returns {{date_from: String, date_to: String}}
 */
export function parseMisPeriod(dateFrom, dateTo, locale) {
    if (isEmpty(dateFrom)) {
        throw new EvaluationError(_t("The start date of the period is missing."));
    }
    if (!isEmpty(dateTo)) {
        return {
            date_from: jsDateToServer(toJsDate(dateFrom, locale)),
            date_to: jsDateToServer(toJsDate(dateTo, locale)),
        };
    }
    const period = toString(dateFrom).trim();
    let found = period.match(QUARTER_REGEXP);
    if (found) {
        const year = Number(found[2]);
        const lastMonth = Number(found[1]) * 3;
        return {
            date_from: serverDate(year, lastMonth - 2, 1),
            date_to: serverDate(year, lastMonth, lastDayOfMonth(year, lastMonth)),
        };
    }
    found = period.match(MONTH_REGEXP);
    if (found) {
        const year = Number(found[2]);
        const month = Number(found[1]);
        return {
            date_from: serverDate(year, month, 1),
            date_to: serverDate(year, month, lastDayOfMonth(year, month)),
        };
    }
    found = period.match(YEAR_REGEXP);
    if (found && Number(found[1]) < 3000) {
        const year = Number(found[1]);
        return {date_from: serverDate(year, 1, 1), date_to: serverDate(year, 12, 31)};
    }
    // A single day
    const day = jsDateToServer(toJsDate(dateFrom, locale));
    return {date_from: day, date_to: day};
}

function parseCompanyIds(companyIds) {
    if (isEmpty(companyIds)) {
        return [];
    }
    const ids = toString(companyIds)
        .split(",")
        .map((id) => Number(id.trim()));
    if (ids.some((id) => !Number.isInteger(id) || id <= 0)) {
        throw new EvaluationError(
            _t("'%s' is not a valid list of company ids.", toString(companyIds))
        );
    }
    return ids.sort((a, b) => a - b);
}

featurePluginRegistry.add("misBuilder", MisBuilderPlugin);

functionRegistry.add("MIS.KPI", {
    description: _t("Get the value of a KPI of a MIS Builder report over a period."),
    args: [
        arg("report (number)", _t("The id of the MIS report template.")),
        arg("kpi (string)", _t("The technical name of the KPI.")),
        arg(
            "date_from (date, string)",
            _t(
                'The start date of the period, or the whole period ("2026", "Q1/2026", "03/2026") when date_to is empty.'
            )
        ),
        arg("date_to (date, optional)", _t("The end date of the period.")),
        arg(
            "company_ids (string, optional)",
            _t(
                "The ids of the companies, separated by a comma (current company if empty)."
            )
        ),
        arg(
            "include_unposted (boolean, default=FALSE)",
            _t("Set to TRUE to include unposted entries.")
        ),
        arg("subkpi (string, optional)", _t("The technical name of the sub-KPI.")),
    ],
    category: "Odoo",
    returns: ["NUMBER"],
    compute: function (
        report,
        kpi,
        dateFrom,
        dateTo = {value: ""},
        companyIds = {value: ""},
        includeUnposted = {value: false},
        subkpi = {value: ""}
    ) {
        const period = parseMisPeriod(dateFrom, dateTo, this.locale);
        const result = this.getters.getMisKpi({
            report_id: toNumber(report, this.locale),
            kpi: toString(kpi).trim(),
            date_from: period.date_from,
            date_to: period.date_to,
            company_ids: parseCompanyIds(companyIds),
            include_unposted: isEmpty(includeUnposted)
                ? false
                : toBoolean(includeUnposted),
            subkpi: isEmpty(subkpi) ? "" : toString(subkpi).trim(),
        });
        const value = result.value === false ? "" : result.value;
        return result.format ? {value, format: result.format} : {value};
    },
});
