This module brings [MIS Builder](https://github.com/OCA/mis-builder) KPIs
into spreadsheets:

- a `MIS.KPI` spreadsheet function returns the value of a KPI of a MIS
  report template over any period;
- a *Spreadsheet* button on MIS report instances creates a spreadsheet
  reproducing the report, where every KPI cell is a live formula.

The data source is the report template (`mis.report`), not the report
instance: periods, companies and options are plain cells of the
spreadsheet, so they can be changed, computed or copied like any other
cell.
