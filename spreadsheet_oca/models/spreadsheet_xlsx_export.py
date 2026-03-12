# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Headless XLSX export.

Server-side generation of .xlsx files from spreadsheet.spreadsheet records,
without requiring a browser session. Addresses the gap described in
odoo/o-spreadsheet Issue #8061 (filed 2026-03-06).

Two rendering strategies:
  1. Static cells: reads cell values from spreadsheet_raw JSON and writes
     them verbatim to the worksheet (preserves text, numbers, booleans).
  2. Pivot sheets: for each ODOO pivot in the spreadsheet JSON, a dedicated
     worksheet is generated with fresh data from _get_pivot_data(). This
     ensures exported pivots reflect the current Odoo database state rather
     than the snapshot saved client-side.

The result is attached to the spreadsheet's Chatter and/or returned as an
ir.actions.act_url download.

Usage from Python:
    xlsx_bytes = SpreadsheetXlsxExporter(env, spreadsheet).render()

Usage from Odoo UI:
    spreadsheet.action_export_xlsx()   # returns download action
"""

import io
import logging

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from odoo import _

from .pivot_data import collect_pivot_summaries

_logger = logging.getLogger(__name__)

# Header row style for pivot sheets
_PIVOT_HEADER_FILL = PatternFill(
    start_color="4472C4", end_color="4472C4", fill_type="solid"
)
_PIVOT_HEADER_FONT = Font(color="FFFFFF", bold=True)
_PIVOT_SUBHEADER_FILL = PatternFill(
    start_color="D6DCF0", end_color="D6DCF0", fill_type="solid"
)
_PIVOT_SUBHEADER_FONT = Font(bold=True)
_PIVOT_TOTAL_FONT = Font(bold=True, italic=True)


class SpreadsheetXlsxExporter:
    """
    Renders a spreadsheet.spreadsheet record to an openpyxl Workbook.

    Call .render() to get a bytes object suitable for attachment or download.
    """

    def __init__(self, env, spreadsheet):
        self.env = env
        self.spreadsheet = spreadsheet
        self.raw = spreadsheet.sudo().spreadsheet_raw or {}

    def render(self):
        """Return the workbook as a bytes object."""
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # remove default empty sheet

        sheets = self.raw.get("sheets", [])

        # ── Render static sheet(s) ────────────────────────────────────────────
        for sheet_def in sheets:
            sheet_name = sheet_def.get("name", "Sheet")[:31]  # Excel limit
            ws = wb.create_sheet(title=sheet_name)
            self._render_static_sheet(ws, sheet_def)

        # ── Render one worksheet per ODOO pivot (with fresh data) ─────────────
        summaries, _failed = collect_pivot_summaries(self.env, self.raw)
        for summary in summaries:
            pivot_name = summary["name"]
            ws_name = (pivot_name[:28] + " +") if len(pivot_name) > 28 else pivot_name
            # Deduplicate sheet names (Excel requires unique names)
            existing = [s.title for s in wb.worksheets]
            if ws_name in existing:
                ws_name = f"{ws_name[:27]}_dup"
            ws = wb.create_sheet(title=ws_name)
            self._render_pivot_sheet_from_result(ws, summary)

        if not wb.worksheets:
            ws = wb.create_sheet(title="Empty")
            ws["A1"] = _("This spreadsheet has no sheets.")

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    # ── Static sheet renderer ─────────────────────────────────────────────────

    def _render_static_sheet(self, ws, sheet_def):
        """Copy static cell values from the sheet JSON to the worksheet.

        Cells are stored as a flat dict keyed by cell address strings
        (e.g. ``"A1"``, ``"B3"``, ``"AA12"``), matching the o-spreadsheet
        native format.
        """
        cells = sheet_def.get("cells", {})
        # cells is {"A1": {content, style, ...}, "B3": {...}, ...}
        for cell_addr, cell_data in cells.items():
            if not isinstance(cell_data, dict):
                continue
            # Parse cell address to (col_idx, row_idx) using our helper
            from .cell_ref import parse_cell_ref

            col_idx, row_idx = parse_cell_ref(cell_addr)
            if col_idx is None:
                continue
            content = cell_data.get("content", "")
            if content is None or content == "":
                continue
            # openpyxl uses 1-based indices
            xl_row = row_idx + 1
            xl_col = col_idx + 1
            # Strip leading "=" for formula cells — write as string
            # (server-side we can't evaluate formulas)
            if isinstance(content, str) and content.startswith("="):
                # Write formula placeholder so user can see what was there
                ws.cell(row=xl_row, column=xl_col).value = content
            else:
                # Try numeric conversion
                ws.cell(row=xl_row, column=xl_col).value = _coerce_value(content)

        # Apply column auto-width (rough estimate)
        _auto_width(ws)

    # ── Pivot sheet renderer ──────────────────────────────────────────────────

    def _render_pivot_sheet_from_result(self, ws, summary):
        """Render a pre-computed pivot summary as a formatted Excel table."""
        display_name = summary["name"]
        model_name = summary["model"]
        result = summary["result"]

        row_dims = result.get("rowDimensions", [])
        col_dims = result.get("colDimensions", [])
        groups = result.get("groups", [])
        measure_specs = result.get("measureSpecs", [])

        # Title row
        title_cell = ws.cell(row=1, column=1, value=display_name)
        title_cell.font = Font(bold=True, size=13)
        ws.merge_cells(
            start_row=1,
            start_column=1,
            end_row=1,
            end_column=max(1, len(row_dims) + len(col_dims) + len(measure_specs)),
        )

        # Subtitle: model + domain
        model_label = model_name
        try:
            model_label = self.env["ir.model"]._get(model_name).name or model_name
        except Exception:
            _logger.debug("Could not resolve model label for %s", model_name)
        ws.cell(row=2, column=1, value=f"{model_label}").font = Font(
            italic=True, color="666666"
        )
        current_row = 4

        # Build a flat table: row_headers | col_headers | measures
        if not row_dims and not col_dims:
            # Grand total only
            current_row = self._write_grand_total(
                ws, groups, measure_specs, current_row
            )
        elif not col_dims:
            # Row-only pivot (simple breakdown)
            current_row = self._write_row_pivot(
                ws, groups, row_dims, measure_specs, current_row
            )
        else:
            # Full cross-tab pivot
            current_row = self._write_crosstab(
                ws, groups, row_dims, col_dims, measure_specs, current_row
            )

        _auto_width(ws)

    def _write_grand_total(self, ws, groups, measure_specs, start_row):
        totals = [g for g in groups if not g["rowGroupBy"] and not g["colGroupBy"]]
        if not totals:
            return start_row
        gt = totals[0]
        # Header
        headers = (
            ["Total"] + [_format_measure_name(m) for m in measure_specs] + ["Count"]
        )
        for ci, h in enumerate(headers, 1):
            cell = ws.cell(row=start_row, column=ci, value=h)
            cell.fill = _PIVOT_HEADER_FILL
            cell.font = _PIVOT_HEADER_FONT
        # Values
        row_vals = [_("Grand Total")]
        for spec in measure_specs:
            row_vals.append(gt.get("measures", {}).get(spec))
        row_vals.append(gt.get("count", 0))
        for ci, v in enumerate(row_vals, 1):
            ws.cell(row=start_row + 1, column=ci, value=v)
        return start_row + 3

    def _write_row_pivot(self, ws, groups, row_dims, measure_specs, start_row):
        row_gb = [d["fieldName"] for d in row_dims]
        row_groups = sorted(
            [g for g in groups if g["rowGroupBy"] == row_gb and not g["colGroupBy"]],
            key=lambda g: [str(v) for v in g["rowValues"]],
        )
        totals = [g for g in groups if not g["rowGroupBy"] and not g["colGroupBy"]]

        # Header row
        headers = [d["fieldName"] for d in row_dims]
        headers += [_format_measure_name(m) for m in measure_specs]
        headers.append("Count")
        for ci, h in enumerate(headers, 1):
            cell = ws.cell(row=start_row, column=ci, value=h)
            cell.fill = _PIVOT_HEADER_FILL
            cell.font = _PIVOT_HEADER_FONT
        r = start_row + 1

        for g in row_groups:
            for ci, v in enumerate(g["rowValues"], 1):
                ws.cell(row=r, column=ci, value=v)
            offset = len(row_dims)
            for si, spec in enumerate(measure_specs):
                ws.cell(
                    row=r, column=offset + si + 1, value=g.get("measures", {}).get(spec)
                )
            ws.cell(
                row=r, column=offset + len(measure_specs) + 1, value=g.get("count", 0)
            )
            r += 1

        # Grand total row
        if totals:
            gt = totals[0]
            cell = ws.cell(row=r, column=1, value=_("Grand Total"))
            cell.font = _PIVOT_TOTAL_FONT
            offset = len(row_dims)
            for si, spec in enumerate(measure_specs):
                c = ws.cell(
                    row=r,
                    column=offset + si + 1,
                    value=gt.get("measures", {}).get(spec),
                )
                c.font = _PIVOT_TOTAL_FONT
            ws.cell(
                row=r, column=offset + len(measure_specs) + 1, value=gt.get("count", 0)
            ).font = _PIVOT_TOTAL_FONT
            r += 1

        return r + 1

    def _write_crosstab(self, ws, groups, row_dims, col_dims, measure_specs, start_row):
        """Write a cross-tab with row headers on left, columns across top."""
        row_gb = [d["fieldName"] for d in row_dims]
        col_gb = [d["fieldName"] for d in col_dims]

        # Collect unique col values
        col_groups = sorted(
            [g for g in groups if g["colGroupBy"] == col_gb and not g["rowGroupBy"]],
            key=lambda g: [str(v) for v in g["colValues"]],
        )
        col_keys = [tuple(g["colValues"]) for g in col_groups]

        # Collect unique row values
        row_groups = sorted(
            [g for g in groups if g["rowGroupBy"] == row_gb and not g["colGroupBy"]],
            key=lambda g: [str(v) for v in g["rowValues"]],
        )

        # Cell value lookup: (row_values_tuple, col_values_tuple) → group
        cell_map = {}
        for g in groups:
            if g["rowGroupBy"] == row_gb and g["colGroupBy"] == col_gb:
                cell_map[(tuple(g["rowValues"]), tuple(g["colValues"]))] = g

        grand_totals = [
            g for g in groups if not g["rowGroupBy"] and not g["colGroupBy"]
        ]

        num_row_dims = len(row_dims)
        total_col = num_row_dims + len(col_keys) * len(measure_specs) + 1

        r = self._write_crosstab_headers(
            ws, row_dims, col_keys, measure_specs, total_col, start_row
        )

        r = self._write_crosstab_data(
            ws,
            row_groups,
            col_keys,
            cell_map,
            groups,
            row_gb,
            num_row_dims,
            measure_specs,
            total_col,
            grand_totals,
            r,
        )

        return r + 1

    def _write_crosstab_headers(
        self, ws, row_dims, col_keys, measure_specs, total_col, r
    ):
        """Write column headers and measure sub-headers for a cross-tab."""
        num_row_dims = len(row_dims)

        for ci in range(num_row_dims):
            cell = ws.cell(row=r, column=ci + 1, value=row_dims[ci]["fieldName"])
            cell.font = Font(bold=True)

        for ki, col_key in enumerate(col_keys):
            label = " / ".join(str(v) for v in col_key) if col_key else _("(none)")
            col_start = num_row_dims + ki * len(measure_specs) + 1
            if len(measure_specs) > 1:
                ws.merge_cells(
                    start_row=r,
                    start_column=col_start,
                    end_row=r,
                    end_column=col_start + len(measure_specs) - 1,
                )
            cell = ws.cell(row=r, column=col_start, value=label)
            cell.fill = _PIVOT_HEADER_FILL
            cell.font = _PIVOT_HEADER_FONT
            cell.alignment = Alignment(horizontal="center")

        if len(measure_specs) > 1:
            ws.merge_cells(
                start_row=r,
                start_column=total_col,
                end_row=r,
                end_column=total_col + len(measure_specs) - 1,
            )
        total_hdr = ws.cell(row=r, column=total_col, value=_("Total"))
        total_hdr.fill = _PIVOT_HEADER_FILL
        total_hdr.font = _PIVOT_HEADER_FONT
        if len(measure_specs) > 1:
            total_hdr.alignment = Alignment(horizontal="center")
        r += 1

        # Measure sub-headers if multiple measures
        if len(measure_specs) > 1:
            for ki in range(len(col_keys)):
                for si, spec in enumerate(measure_specs):
                    col_start = num_row_dims + ki * len(measure_specs) + si + 1
                    cell = ws.cell(
                        row=r,
                        column=col_start,
                        value=_format_measure_name(spec),
                    )
                    cell.fill = _PIVOT_SUBHEADER_FILL
                    cell.font = _PIVOT_SUBHEADER_FONT
            for si, spec in enumerate(measure_specs):
                cell = ws.cell(
                    row=r,
                    column=total_col + si,
                    value=_format_measure_name(spec),
                )
                cell.fill = _PIVOT_SUBHEADER_FILL
                cell.font = _PIVOT_SUBHEADER_FONT
            r += 1

        return r

    def _write_crosstab_data(
        self,
        ws,
        row_groups,
        col_keys,
        cell_map,
        groups,
        row_gb,
        num_row_dims,
        measure_specs,
        total_col,
        grand_totals,
        r,
    ):
        """Write data rows and grand total for a cross-tab."""
        for rg in row_groups:
            row_key = tuple(rg["rowValues"])
            for ci, v in enumerate(rg["rowValues"], 1):
                ws.cell(row=r, column=ci, value=v)
            for ki, col_key in enumerate(col_keys):
                cell_group = cell_map.get((row_key, col_key))
                for si, spec in enumerate(measure_specs):
                    col_pos = num_row_dims + ki * len(measure_specs) + si + 1
                    val = (
                        cell_group.get("measures", {}).get(spec) if cell_group else None
                    )
                    ws.cell(row=r, column=col_pos, value=val)
            # Row totals
            row_total = [
                g
                for g in groups
                if g["rowGroupBy"] == row_gb
                and not g["colGroupBy"]
                and tuple(g["rowValues"]) == row_key
            ]
            if row_total:
                for si, spec in enumerate(measure_specs):
                    v = row_total[0].get("measures", {}).get(spec)
                    ws.cell(
                        row=r, column=total_col + si, value=v
                    ).font = _PIVOT_TOTAL_FONT
            r += 1

        # Grand total row
        if grand_totals:
            gt = grand_totals[0]
            cell = ws.cell(row=r, column=1, value=_("Grand Total"))
            cell.font = _PIVOT_TOTAL_FONT
            for si, spec in enumerate(measure_specs):
                ws.cell(
                    row=r,
                    column=total_col + si,
                    value=gt.get("measures", {}).get(spec),
                ).font = _PIVOT_TOTAL_FONT
            r += 1

        return r


def _coerce_value(v):
    """Try to return v as int or float; otherwise return the string."""
    if isinstance(v, int | float | bool):
        return v
    s = str(v).strip()
    try:
        return int(s)
    except (ValueError, TypeError):
        _logger.debug("_coerce_value: %r is not an integer", s)
    try:
        return float(s.replace(",", ""))
    except (ValueError, TypeError):
        _logger.debug("_coerce_value: %r is not a float", s)
    return s


def _format_measure_name(spec):
    """Turn 'amount_total:sum' into 'Amount Total (Sum)'."""
    if ":" in spec:
        field, agg = spec.split(":", 1)
        return f"{field.replace('_', ' ').title()} ({agg.title()})"
    return spec.replace("_", " ").title()


def _auto_width(ws, max_width=60):
    """Set approximate column widths based on cell content length."""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_len + 4, max_width)
