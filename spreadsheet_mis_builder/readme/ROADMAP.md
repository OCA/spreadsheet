- Columns that `MIS.KPI` can not reproduce are exported as static
  values, and flagged as such in their header: analytic filters,
  alternative move line sources and budgets (`mis_builder_budget`).
- Details by account are not exported.
- Rows hidden when empty are evaluated at export time only.
- The divider, prefix and suffix of MIS styles are not converted.
- The export always creates a new spreadsheet: inserting into an
  existing one is not supported.
- No autocompletion of report and KPI names, no drill-down to journal
  items from a cell, and no side panel to manage the parameters.
- The base date is a cell; it is not linked to the global filters of the
  spreadsheet.
