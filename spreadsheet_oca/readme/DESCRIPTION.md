This module provides a full-featured spreadsheet editor for Odoo CE using
the ``o-spreadsheet`` engine. It serves as a community alternative that
requires only Odoo CE and OCA dependencies.

Beyond basic spreadsheet editing, the module includes server-side features
for operational use:

- **Scheduled Refresh** — cron-based pivot data refresh with email digest
  notifications and input parameter substitution in domains
- **KPI Alerts** — cell-value threshold monitors with edge or level trigger
  modes, sending notifications when conditions are met
- **What-If Scenarios** — named cell-override sets for scenario planning,
  with comparison export and apply-to-copy workflow
- **Email Subscriptions** — partner-level daily/weekly/monthly digest emails
  with optional pivot data summaries
- **Input Parameters** — named cell registry for domain token substitution
  (e.g. ``%(start_date)s``) used by scheduled refresh and alerts
- **Cell Writeback** — edit Odoo record fields directly from list-view cells
  in the spreadsheet, with full audit trail and rollback
- **XLSX Export** — server-rendered ``.xlsx`` download with fresh pivot data
  on dedicated sheets, styled headers, and static cell content
- **Collaborative Editing** — revision-based multi-user editing with conflict
  resolution via the OWL-based spreadsheet component
