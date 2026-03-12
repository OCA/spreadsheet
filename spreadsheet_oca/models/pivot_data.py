# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Server-side pivot data helper.

Replicates the read_group strategy used by the Odoo web PivotModel
(addons/web/static/src/views/pivot/pivot_model.js) to produce pivot table
data server-side, without executing any JavaScript.

The JS pivot loads data by:
  1. Computing all row-groupby prefixes ("sections"):
       rows=["partner_id","date:month"]  →  [[], ["partner_id"],
                                              ["partner_id","date:month"]]
  2. Computing all col-groupby prefixes ("sections"):
       cols=["stage_id"]                 →  [[], ["stage_id"]]
  3. Taking the cartesian product (row_prefix × col_prefix) for "divisors".
  4. For each divisor [rowPrefix, colPrefix], calling:
       read_group(domain, fields=measureSpecs,
                  groupby=rowPrefix+colPrefix, lazy=False)

This module replicates that strategy in Python and exposes:
  - ``get_pivot_data(model, domain, context, rows, columns, measures)``

Rows / columns are lists of dimension dicts:
  {"fieldName": "date_order", "granularity": "month"}
  {"fieldName": "partner_id"}                            (no granularity)

Measures are lists of measure dicts:
  {"fieldName": "amount_total", "aggregator": "sum"}
  {"fieldName": "__count"}
"""

import itertools
import logging

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers mirroring the JS helpers in pivot_model.js
# ---------------------------------------------------------------------------

DATE_GRANULARITIES = {"day", "week", "month", "quarter", "year"}


def _dimension_to_groupby(dim):
    """Convert a dimension dict to an Odoo read_group groupby string.

    {"fieldName": "date_order", "granularity": "month"}  →  "date_order:month"
    {"fieldName": "partner_id"}                           →  "partner_id"
    """
    name = dim["fieldName"]
    gran = dim.get("granularity")
    return f"{name}:{gran}" if gran else name


def _sections(lst):
    """Return all prefixes of lst including the empty prefix.

    sections(["a", "b", "c"]) → [[], ["a"], ["a", "b"], ["a", "b", "c"]]

    Mirrors the JS ``sections()`` helper.
    """
    return [lst[:i] for i in range(len(lst) + 1)]


def _measure_to_field_spec(measure):
    """Convert a measure dict to a read_group ``fields`` element.

    {"fieldName": "amount_total", "aggregator": "sum"}  →  "amount_total:sum"
    {"fieldName": "__count"}                             →  "__count"
    """
    if measure["fieldName"] == "__count":
        return "__count"
    agg = measure.get("aggregator") or "sum"
    return f"{measure['fieldName']}:{agg}"


# ---------------------------------------------------------------------------
# Main computation
# ---------------------------------------------------------------------------


def _get_pivot_data(env, model_name, domain, context, row_dims, col_dims, measures):
    """Compute pivot table data using the same read_group strategy as the JS.

    Returns a dict:
    {
        "fields": {fieldName: {type, string, ...}},
        "groups": [
            {
                "rowValues": ["2026-01", ...],    # normalised group key values
                "colValues": ["Confirmed", ...],
                "rowGroupBy": ["date_order:month"],
                "colGroupBy": ["stage_id"],
                "count": 12,
                "measures": {"amount_total:sum": 9800.0, ...},
            },
            ...
        ],
        "rowDimensions":  [{"fieldName": ..., "granularity": ...}, ...],
        "colDimensions":  [{"fieldName": ..., "granularity": ...}, ...],
        "measureSpecs":   ["amount_total:sum", ...],
    }
    """
    Model = env[model_name].with_context(**(context or {}))

    # ── 1. Fields metadata (needed for label resolution) ─────────────────
    all_field_names = [d["fieldName"] for d in row_dims + col_dims] + [
        m["fieldName"] for m in measures if m["fieldName"] != "__count"
    ]
    # fields_get returns {fieldName: {type, string, selection, ...}}
    fields_meta = Model.fields_get(
        all_field_names, attributes=["type", "string", "selection"]
    )

    # ── 2. Build groupby strings ──────────────────────────────────────────
    row_groupbys = [_dimension_to_groupby(d) for d in row_dims]
    col_groupbys = [_dimension_to_groupby(d) for d in col_dims]
    measure_specs = [_measure_to_field_spec(m) for m in measures]

    # Ensure count is always fetched (JS always adds __count implicitly)
    field_specs_with_count = measure_specs + (
        [] if "__count" in measure_specs else ["__count"]
    )

    # ── 3. Compute divisors (cartesian product of all prefixes) ──────────
    row_sections = _sections(row_groupbys)
    col_sections = _sections(col_groupbys)
    divisors = list(itertools.product(row_sections, col_sections))

    # ── 4. Fire read_group for each divisor ──────────────────────────────
    groups = []
    for row_prefix, col_prefix in divisors:
        groupby = row_prefix + col_prefix
        try:
            results = Model.read_group(
                domain=domain or [],
                fields=field_specs_with_count,
                groupby=groupby,
                lazy=False,
            )
        except Exception:
            _logger.exception(
                "read_group failed for model=%s groupby=%s", model_name, groupby
            )
            continue

        for rg in results:
            group_entry = {
                "rowGroupBy": row_prefix,
                "colGroupBy": col_prefix,
                "rowValues": _extract_group_values(rg, row_prefix, fields_meta),
                "colValues": _extract_group_values(rg, col_prefix, fields_meta),
                "count": rg.get("__count", 0),
                "measures": _extract_measures(rg, measures, fields_meta),
                "domain": rg.get("__domain", []),
            }
            groups.append(group_entry)

    return {
        "fields": fields_meta,
        "groups": groups,
        "rowDimensions": row_dims,
        "colDimensions": col_dims,
        "measureSpecs": measure_specs,
    }


def _extract_group_values(rg_row, groupby_list, fields_meta):
    """Extract normalised group values from a read_group result row.

    Many2one fields return (id, display_name) — we normalise to the id (int).
    Date/datetime fields return a formatted string (Odoo already handles
    granularity in the groupby key).
    """
    values = []
    for gb_spec in groupby_list:
        field_name = gb_spec.split(":")[0]
        raw = rg_row.get(gb_spec) or rg_row.get(field_name)
        if raw is False or raw is None:
            values.append(False)
        elif isinstance(raw, list | tuple) and len(raw) == 2:
            # Many2one: (id, display_name) — store id; JS uses id for grouping
            values.append(raw[0])
        else:
            values.append(raw)
    return values


def _extract_measures(rg_row, measures, fields_meta):
    """Extract measure values from a read_group result row."""
    result = {}
    for measure in measures:
        fname = measure["fieldName"]
        agg = measure.get("aggregator")
        if fname == "__count":
            result["__count"] = rg_row.get("__count", 0)
            continue
        # read_group key: field_name (no aggregator suffix in result keys)
        raw = rg_row.get(fname, 0)
        if isinstance(raw, list | tuple):
            # Many2one used as measure — count distinct occurrences
            raw = 1 if raw else 0
        if raw is False:
            raw = 0
        spec_key = f"{fname}:{agg}" if agg else fname
        result[spec_key] = raw
    return result


# ---------------------------------------------------------------------------
# Shared helpers for pivot iteration and HTML rendering
# ---------------------------------------------------------------------------


def collect_pivot_summaries(env, spreadsheet_raw, domain_transform=None):
    """Iterate over ODOO-type pivots and return fresh data for each.

    Args:
        env: Odoo environment.
        spreadsheet_raw: dict — the spreadsheet's raw JSON data.
        domain_transform: optional callable(domain) -> domain, applied to each
            pivot's domain before querying (e.g. parameter substitution).

    Returns:
        A tuple ``(summaries, failed_names)`` where *summaries* is a list of
        ``{"name": ..., "model": ..., "result": ...}`` dicts, and
        *failed_names* is a list of pivot display names that could not be loaded.
    """
    pivots = spreadsheet_raw.get("pivots", {})
    summaries = []
    failed_names = []
    for pivot_id, pivot_def in pivots.items():
        if pivot_def.get("type") != "ODOO":
            continue
        model_name = pivot_def.get("model")
        pivot_name = pivot_def.get("name") or f"Pivot #{pivot_id}"
        if not model_name or model_name not in env:
            _logger.warning(
                "collect_pivot_summaries: unknown model %r — skipping pivot %s",
                model_name,
                pivot_id,
            )
            failed_names.append(pivot_name)
            continue
        try:
            domain = pivot_def.get("domain", [])
            if domain_transform:
                domain = domain_transform(domain)
            result = _get_pivot_data(
                env,
                model_name,
                domain,
                pivot_def.get("context", {}),
                pivot_def.get("rows", []),
                pivot_def.get("columns", []),
                pivot_def.get("measures", []),
            )
            summaries.append(
                {
                    "name": pivot_name,
                    "model": model_name,
                    "result": result,
                }
            )
        except Exception:
            _logger.exception(
                "collect_pivot_summaries: failed to compute pivot %s",
                pivot_id,
            )
            failed_names.append(pivot_name)
    return summaries, failed_names


def render_pivot_table_html(summary, max_rows=10):
    """Render a single pivot summary as an HTML table string.

    Args:
        summary: dict with keys ``"name"``, ``"model"``, ``"result"``
            (as returned by ``collect_pivot_summaries``).
        max_rows: maximum number of detail rows to include before truncating.

    Returns:
        str — HTML fragment for the pivot table.
    """
    result = summary["result"]
    name = summary["name"]
    model = summary["model"]
    parts = []

    parts.append(
        f'<h3 style="margin:0 0 6px 0;font-size:15px">{name}'
        f' <span style="font-size:12px;color:#888'
        f';font-weight:normal">({model})</span></h3>'
    )

    row_dims = result.get("rowDimensions", [])
    groups = result.get("groups", [])

    # Grand total row
    grand_totals = [
        g for g in groups if g["rowGroupBy"] == [] and g["colGroupBy"] == []
    ]
    if grand_totals:
        gt = grand_totals[0]
        count = gt.get("count", 0)
        parts.append(
            f'<p style="margin:2px 0"><strong>Total records:</strong> {count}</p>'
        )
        for key, val in gt.get("measures", {}).items():
            if key != "__count" and val is not None:
                parts.append(
                    f'<p style="margin:2px 0"><strong>{key}:</strong> {val}</p>'
                )

    # Row breakdown table
    if row_dims:
        row_gb = [d["fieldName"] for d in row_dims]
        row_groups = [
            g for g in groups if g["rowGroupBy"] == row_gb and g["colGroupBy"] == []
        ]
        if row_groups:
            measure_keys = [
                k for k in (row_groups[0].get("measures") or {}) if k != "__count"
            ]
            headers = ["Group"] + measure_keys + ["Count"]
            parts.append(
                '<table style="border-collapse:collapse;font-size:12px;'
                'width:100%;margin-top:8px">'
            )
            parts.append("<thead><tr>")
            for h in headers:
                parts.append(
                    '<th style="border:1px solid #ddd;padding:5px 8px;'
                    f'background:#eef;text-align:left;white-space:nowrap">{h}</th>'
                )
            parts.append("</tr></thead><tbody>")
            for g in row_groups[:max_rows]:
                label = ", ".join(str(v) for v in g["rowValues"])
                parts.append("<tr>")
                parts.append(
                    f'<td style="border:1px solid #ddd;padding:4px 8px">{label}</td>'
                )
                for mk in measure_keys:
                    val = g.get("measures", {}).get(mk, "")
                    parts.append(
                        '<td style="border:1px solid #ddd;padding:4px 8px;'
                        f'text-align:right">{val}</td>'
                    )
                parts.append(
                    '<td style="border:1px solid #ddd;padding:4px 8px;'
                    'text-align:right">{}</td>'.format(g.get("count", ""))
                )
                parts.append("</tr>")
            if len(row_groups) > max_rows:
                colspan = len(headers)
                extra = len(row_groups) - max_rows
                more_text = f"and {extra} more rows"
                parts.append(
                    f'<tr><td colspan="{colspan}"'
                    f' style="padding:4px 8px;color:#888">'
                    f"… {more_text}</td></tr>"
                )
            parts.append("</tbody></table>")

    return "".join(parts)
