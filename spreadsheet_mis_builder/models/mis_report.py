# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.mis_builder.models.accounting_none import AccountingNone
from odoo.addons.mis_builder.models.mis_report_style import TYPE_NUM, TYPE_PCT


class MisReport(models.Model):
    _inherit = "mis.report"

    @api.model
    def _spreadsheet_number_format(self, var_type, style_props):
        """Spreadsheet number format matching a KPI type and style."""
        if var_type not in (TYPE_NUM, TYPE_PCT):
            return False
        dp = style_props.dp or 0
        decimals = "." + "0" * dp if dp else ""
        if var_type == TYPE_PCT:
            return f"0{decimals}%"
        return f"#,##0{decimals}"

    def _spreadsheet_kpi_format(self, kpi):
        self.ensure_one()
        style_model = self.env["mis.report.style"]
        style_props = style_model.merge([self.style_id, kpi.style_id])
        return self._spreadsheet_number_format(kpi.type, style_props)

    def _spreadsheet_companies(self, company_ids):
        if not company_ids:
            return self.env.company
        companies = self.env["res.company"].browse(company_ids).exists()
        forbidden = companies - self.env.user.company_ids
        if len(companies) != len(company_ids) or forbidden:
            raise UserError(
                self.env._(
                    "Unknown or unauthorized companies: %s",
                    ", ".join(str(c) for c in company_ids),
                )
            )
        return companies

    @api.model
    def _spreadsheet_evaluate(self, args, cache):
        """Evaluate all the KPIs of a report for one set of parameters.

        The result is cached by parameters, so that all the cells of a
        spreadsheet column cost one single report evaluation.
        """
        company_ids = tuple(sorted(set(args.get("company_ids") or [])))
        key = (
            args["report_id"],
            args["date_from"],
            args["date_to"],
            company_ids,
            bool(args.get("include_unposted")),
            args.get("subkpi") or "",
        )
        if key in cache:
            return cache[key]
        report = self.browse(args["report_id"]).exists()
        if not report:
            raise UserError(
                self.env._("MIS report template %s not found.", args["report_id"])
            )
        companies = report._spreadsheet_companies(list(company_ids))
        report = report.with_context(allowed_company_ids=companies.ids)
        companies = companies.with_context(allowed_company_ids=companies.ids)
        date_from = fields.Date.to_date(args["date_from"])
        date_to = fields.Date.to_date(args["date_to"])
        if date_from > date_to:
            raise UserError(self.env._("The start date is after the end date."))
        subkpi = report.env["mis.report.subkpi"]
        if key[5]:
            subkpi = report.subkpi_ids.filtered(lambda s: s.name == key[5])
            if not subkpi:
                raise UserError(
                    self.env._(
                        "Sub-KPI %(subkpi)s not found in report %(report)s.",
                        subkpi=key[5],
                        report=report.display_name,
                    )
                )
        aep_key = ("aep", report.id, company_ids)
        if aep_key not in cache:
            cache[aep_key] = report._prepare_aep(companies)
        values = report.evaluate(
            cache[aep_key],
            date_from,
            date_to,
            target_move="all" if key[4] else "posted",
            subkpis_filter=subkpi or None,
        )
        cache[key] = (report, values)
        return cache[key]

    @api.model
    def _spreadsheet_fetch_one_kpi(self, args, cache):
        report, values = self._spreadsheet_evaluate(args, cache)
        kpi = report.kpi_ids.filtered(lambda k: k.name == args["kpi"])
        if not kpi:
            raise UserError(
                self.env._(
                    "KPI %(kpi)s not found in report %(report)s.",
                    kpi=args["kpi"],
                    report=report.display_name,
                )
            )
        if kpi.name not in values:
            raise UserError(
                self.env._("KPI %s could not be evaluated.", kpi.name),
            )
        value = values[kpi.name]
        if isinstance(value, tuple):
            if len(value) != 1:
                raise UserError(
                    self.env._(
                        "KPI %(kpi)s has several sub-KPIs (%(subkpis)s): "
                        "one of them must be given.",
                        kpi=kpi.name,
                        subkpis=", ".join(report.subkpi_ids.mapped("name")),
                    )
                )
            value = value[0]
        if value is AccountingNone or value is None:
            value = False
        return {"value": value, "format": report._spreadsheet_kpi_format(kpi)}

    @api.model
    def spreadsheet_fetch_kpi(self, args_list):
        """Batch endpoint of the MIS.KPI spreadsheet function.

        :param args_list: list of dicts with keys ``report_id``, ``kpi``,
            ``date_from``, ``date_to`` and optionally ``company_ids``,
            ``include_unposted`` and ``subkpi``
        :return: list of dicts, in the same order, with either ``value``
            and ``format``, or ``error``
        """
        cache = {}
        results = []
        for args in args_list:
            try:
                results.append(self._spreadsheet_fetch_one_kpi(args, cache))
            except UserError as e:
                results.append({"error": str(e)})
        return results
