If you want to develop custom business functions, you can add others,
based on the file
<https://github.com/odoo/odoo/blob/16.0/addons/spreadsheet_account/static/src/accounting_functions.js>

## Server-side pivot computation

`models/pivot_data.py` reproduces the strategy of the JavaScript
`PivotModel` (`web/static/src/views/pivot/pivot_model.js`) in Python, so
pivot data can be produced without a browser — for scheduled refreshes,
emails or exports.

For row groupbys `R` and column groupbys `C` it queries every *prefix*
pair of `R` and `C` (the "divisors"), which is what produces the subtotal
rows a pivot needs. That means **(len(R)+1) x (len(C)+1) queries** per
pivot, matching what the JS does.

The useful entry points are:

- `get_pivot_data(env, model, domain, context, rows, cols, measures)` —
  one pivot. Groups come back with `rowValues`/`colValues` (ids, for
  grouping) and `rowLabels`/`colLabels` (display names, for rendering).
  If a subtotal query fails the result is still returned, but flagged
  with `partial` and `failedGroupBys`; an `AccessError` is re-raised
  rather than degraded into an empty group.
- `collect_pivot_summaries(env, spreadsheet_raw, domain_transform=None)` —
  every Odoo pivot in a workbook.
- `render_pivot_table_html(summary, max_rows=10)` — one summary as HTML.

`models/cell_ref.py` holds the A1-notation helpers used to read and write
individual cells of the `spreadsheet_raw` JSON.
