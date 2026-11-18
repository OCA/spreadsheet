# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import ast

from odoo import fields, models

from odoo.addons.mis_builder.models.accounting_none import AccountingNone
from odoo.addons.mis_builder.models.data_error import DataError
from odoo.addons.mis_builder.models.mis_report_instance import (
    MODE_REL,
    SRC_ACTUALS,
    SRC_CMPCOL,
    SRC_SUMCOL,
)
from odoo.addons.mis_builder.models.mis_report_style import (
    CMP_DIFF,
    CMP_PCT,
    TYPE_NUM,
    TYPE_PCT,
)

FONT_SIZES = {
    "xx-small": 7,
    "x-small": 8,
    "small": 9,
    "medium": 10,
    "large": 12,
    "x-large": 14,
    "xx-large": 18,
}
# Cells holding the parameters shared by all the formulas of the sheet.
CELL_REPORT = "$B$2"
CELL_COMPANIES = "$B$3"
CELL_UNPOSTED = "$B$4"
CELL_BASE_DATE = "$B$5"
ROW_FROM = 7
ROW_TO = 8
ROW_LABELS = 9


def _col_letter(index):
    """Zero-based column index to spreadsheet column letters."""
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _xc(col, row):
    return f"{_col_letter(col)}{row}"


def _date_formula(date):
    return f"=DATE({date.year},{date.month},{date.day})"


class SheetBuilder:
    """Accumulate the cells of one sheet in the o-spreadsheet data format."""

    def __init__(self):
        self.cells = {}
        self.cell_styles = {}
        self.cell_formats = {}
        self.styles = {}
        self.formats = {}
        self.col_number = 1
        self.row_number = 1

    @staticmethod
    def _registry_id(registry, value):
        for key, existing in registry.items():
            if existing == value:
                return key
        key = len(registry) + 1
        registry[key] = value
        return key

    def set(self, col, row, content=None, style=None, number_format=None):
        xc = _xc(col, row)
        if content not in (None, False, ""):
            self.cells[xc] = {"content": str(content)}
        if style:
            self.cell_styles[xc] = self._registry_id(self.styles, style)
        if number_format:
            self.cell_formats[xc] = self._registry_id(self.formats, number_format)
        self.col_number = max(self.col_number, col + 1)
        self.row_number = max(self.row_number, row)


class MisReportInstance(models.Model):
    _inherit = "mis.report.instance"

    def action_export_spreadsheet(self):
        """Create a spreadsheet with live formulas from this report."""
        self.ensure_one()
        spreadsheet = self.env["spreadsheet.spreadsheet"].create(
            {"name": self.name, "spreadsheet_raw": self._spreadsheet_data()}
        )
        return spreadsheet.open_spreadsheet()

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------

    def _spreadsheet_is_live_period(self, period):
        """Tell if the values of a column can be computed by MIS.KPI.

        Columns the function can not reproduce (alternative move line
        sources, analytic filters, budgets...) are exported as static values.
        """
        return (
            period.source == SRC_ACTUALS
            and period.source_aml_model_name in (False, "account.move.line")
            and not ast.literal_eval(self.analytic_domain or "[]")
            and not ast.literal_eval(period.analytic_domain or "[]")
            and not self.env.context.get("mis_analytic_domain")
            and bool(period.date_from and period.date_to)
        )

    def _spreadsheet_period_dates(self, period, col):
        """Formulas for the start and end dates of a live column."""
        date_from = fields.Date.to_date(period.date_from)
        date_to = fields.Date.to_date(period.date_to)
        formula_from = _date_formula(date_from)
        formula_to = _date_formula(date_to)
        if not self.comparison_mode or period.mode != MODE_REL:
            return formula_from, formula_to
        base = CELL_BASE_DATE
        offset = period.offset
        duration = period.duration
        cell_from = _xc(col, ROW_FROM)
        if period.type == "d":
            formula_from = f"={base}+{offset}"
            formula_to = f"={cell_from}+{duration - 1}"
        elif period.type == "w":
            formula_from = f"={base}-WEEKDAY({base},2)+1+{7 * offset}"
            formula_to = f"={cell_from}+{7 * duration - 1}"
        elif period.type == "m":
            formula_from = f"=EDATE(EOMONTH({base},-1)+1,{offset})"
            formula_to = f"=EOMONTH({base},{offset + duration - 1})"
        elif period.type == "y":
            formula_from = f"=DATE(YEAR({base})+{offset},1,1)"
            formula_to = f"=DATE(YEAR({base})+{offset + duration - 1},12,31)"
        if period.is_ytd:
            formula_from = f"=DATE(YEAR({_xc(col, ROW_TO)}),1,1)"
        return formula_from, formula_to

    # ------------------------------------------------------------------
    # Cells
    # ------------------------------------------------------------------

    def _spreadsheet_style(self, style_props):
        style = {}
        if style_props.font_weight == "bold":
            style["bold"] = True
        if style_props.font_style == "italic":
            style["italic"] = True
        if style_props.color:
            style["textColor"] = style_props.color
        if style_props.background_color:
            style["fillColor"] = style_props.background_color
        if style_props.font_size in FONT_SIZES:
            style["fontSize"] = FONT_SIZES[style_props.font_size]
        return style

    def _spreadsheet_static_value(self, cell):
        if (
            cell is None
            or cell.val is AccountingNone
            or isinstance(cell.val, DataError)
        ):
            return None
        if isinstance(cell.val, bool | int | float):
            return repr(cell.val)
        return cell.val

    def _spreadsheet_kpi_formula(self, kpi, col, subkpi):
        formula = (
            f'=MIS.KPI({CELL_REPORT},"{kpi.name}",'
            f"{_col_letter(col)}${ROW_FROM},{_col_letter(col)}${ROW_TO},"
            f"{CELL_COMPANIES},{CELL_UNPOSTED}"
        )
        if subkpi:
            formula += f',"{subkpi.name}"'
        return formula + ")"

    def _spreadsheet_comparison(self, kpi, style_props, cell_to, cell_from):
        """Formula and format comparing two cells, as MIS Builder does."""
        report = self.report_id
        if kpi.type == TYPE_PCT:
            dp = style_props.dp or 0
            decimals = "." + "0" * dp if dp else ""
            return f"=({cell_to}-{cell_from})*100", f"0{decimals}[$ pp]"
        if kpi.type != TYPE_NUM:
            return None, None
        if kpi.compare_method == CMP_DIFF:
            return (
                f"={cell_to}-{cell_from}",
                report._spreadsheet_number_format(TYPE_NUM, style_props),
            )
        if kpi.compare_method == CMP_PCT:
            return (
                f'=IF({cell_from}=0,"",({cell_to}-{cell_from})/ABS({cell_from}))',
                "0.0%",
            )
        return None, None

    # ------------------------------------------------------------------
    # Sheet
    # ------------------------------------------------------------------

    def _spreadsheet_data(self):
        """Spreadsheet (o-spreadsheet data) reproducing this report.

        KPI cells are MIS.KPI formulas, period dates are formulas relative
        to a base date cell, and sum and comparison columns are plain cell
        formulas, so that the spreadsheet stays live and editable.
        """
        self.ensure_one()
        report = self.report_id
        matrix = self._compute_matrix()
        periods = {period.id: period for period in self.period_ids}
        sheet = SheetBuilder()
        bold = {"bold": True}
        muted = {"textColor": "#666666", "italic": True}
        lang = self.env["res.lang"]._lang_get(self.env.user.lang)
        locale = lang._odoo_lang_to_spreadsheet_locale()
        date_format = locale.get("dateFormat") or "yyyy-mm-dd"

        # parameters
        companies = self.query_company_ids
        sheet.set(0, 1, self.name, {"bold": True, "fontSize": 14})
        sheet.set(0, 2, self.env._("Report"), bold)
        sheet.set(1, 2, report.id)
        sheet.set(2, 2, report.name, muted)
        sheet.set(0, 3, self.env._("Companies"), bold)
        company_ids = ",".join(str(c) for c in companies.ids)
        sheet.set(1, 3, f'="{company_ids}"')
        sheet.set(2, 3, ", ".join(companies.mapped("name")), muted)
        sheet.set(0, 4, self.env._("Include unposted entries"), bold)
        sheet.set(1, 4, "TRUE" if self.target_move == "all" else "FALSE")
        if self.comparison_mode:
            sheet.set(0, 5, self.env._("Base date"), bold)
            base_date = _date_formula(self.pivot_date) if self.date else "=TODAY()"
            sheet.set(1, 5, base_date, number_format=date_format)
        sheet.set(0, ROW_FROM, self.env._("From"), bold)
        sheet.set(0, ROW_TO, self.env._("To"), bold)

        # columns
        has_subcols = any(col.subkpis for col in matrix.iter_cols())
        first_row = ROW_LABELS + (2 if has_subcols else 1)
        col_index = {}  # {(period id, sub column index): column}
        next_col = 1
        for col in matrix.iter_cols():
            period = periods[col.key]
            live = self._spreadsheet_is_live_period(period)
            label = col.label
            if not live and period.source not in (SRC_SUMCOL, SRC_CMPCOL):
                label = self.env._("%s (static)", label)
            for subcol in col.iter_subcols():
                col_index[(col.key, subcol.index)] = next_col
                if subcol.index == 0:
                    sheet.set(next_col, ROW_LABELS, label, bold)
                if has_subcols:
                    sheet.set(next_col, ROW_LABELS + 1, subcol.label, bold)
                if live:
                    date_from, date_to = self._spreadsheet_period_dates(
                        period, next_col
                    )
                    sheet.set(next_col, ROW_FROM, date_from, None, date_format)
                    sheet.set(next_col, ROW_TO, date_to, None, date_format)
                next_col += 1

        # rows
        sheet_row = first_row
        for row in matrix.iter_rows():
            if row.account_id:
                # details by account are not exported
                continue
            props = row.style_props
            if props.hide_always or (props.hide_empty and row.is_empty()):
                continue
            indent = " " * 4 * (props.indent_level or 0)
            sheet.set(0, sheet_row, indent + row.label, self._spreadsheet_style(props))
            for col in matrix.iter_cols():
                period = periods[col.key]
                live = self._spreadsheet_is_live_period(period)
                for subcol in col.iter_subcols():
                    self._spreadsheet_set_cell(
                        sheet, sheet_row, row, period, live, subcol, col_index
                    )
            sheet_row += 1

        data = self.env["spreadsheet.spreadsheet"]._empty_spreadsheet_data()
        data.update(
            {
                "version": 21,
                "styles": {str(k): v for k, v in sheet.styles.items()},
                "formats": {str(k): v for k, v in sheet.formats.items()},
            }
        )
        cols = {str(i): {"size": 130} for i in range(1, sheet.col_number)}
        cols["0"] = {"size": 280}
        data["sheets"][0].update(
            {
                "name": self.env._("MIS Report"),
                "colNumber": max(sheet.col_number + 5, 26),
                "rowNumber": max(sheet.row_number + 20, 100),
                "cols": cols,
                "cells": sheet.cells,
                "styles": sheet.cell_styles,
                "formats": sheet.cell_formats,
            }
        )
        return data

    def _spreadsheet_set_cell(
        self, sheet, sheet_row, row, period, live, subcol, col_index
    ):
        kpi = row.kpi
        report = self.report_id
        sheet_col = col_index[(period.id, subcol.index)]
        cell = subcol.get_cell_for_row(row)
        props = cell.style_props if cell is not None else row.style_props
        style = self._spreadsheet_style(props)
        number_format = report._spreadsheet_number_format(kpi.type, props)
        content = None

        def source_cell(source_period):
            source_col = col_index.get((source_period.id, subcol.index))
            return _xc(source_col, sheet_row) if source_col else None

        if live:
            content = self._spreadsheet_kpi_formula(kpi, sheet_col, subcol.subkpi)
        elif period.source == SRC_SUMCOL:
            terms = [
                (sumcol.sign, source_cell(sumcol.period_to_sum_id))
                for sumcol in period.source_sumcol_ids
            ]
            if terms and all(ref for _sign, ref in terms):
                content = "=" + "".join(sign + ref for sign, ref in terms)
        elif period.source == SRC_CMPCOL:
            cell_to = source_cell(period.source_cmpcol_to_id)
            cell_from = source_cell(period.source_cmpcol_from_id)
            if cell_to and cell_from:
                content, number_format = self._spreadsheet_comparison(
                    kpi, props, cell_to, cell_from
                )
            else:
                number_format = None
        if content is None and period.source != SRC_CMPCOL:
            content = self._spreadsheet_static_value(cell)
            if cell is not None and cell.val_type != kpi.type:
                number_format = report._spreadsheet_number_format(cell.val_type, props)
        sheet.set(sheet_col, sheet_row, content, style, number_format)
