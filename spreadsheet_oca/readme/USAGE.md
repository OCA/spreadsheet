## Create a Spreadsheet

- Go to the **Spreadsheet** menu
- Click **Create**, enter a name, then click **Edit** to open the editor

![](../static/description/spreadsheet_create.png)

The editor uses ``o-spreadsheet`` and supports standard functions like
``SUM()``, ``AVERAGE()``, etc. For the full function list, see
<https://github.com/odoo/o-spreadsheet/> or <https://odoo.github.io/o-spreadsheet/>.

![](../static/description/spreadsheet_edit.png)

## Pivot Tables

Insert an Odoo pivot into the spreadsheet using ``PIVOT.VALUE()`` and
``PIVOT.HEADER()`` formulas. The pivot definition (model, domain, measures,
row/column groupings) is stored in the spreadsheet JSON and evaluated
against live Odoo data.

Use **Data > Refresh All Data** in the spreadsheet toolbar to reload pivot
values from the database.

## Scheduled Refresh

On any spreadsheet form, click **Refresh Schedules** to create a schedule:

- Set the interval (hours, days, weeks, or months)
- Add notification partners who receive an email digest after each refresh
- Click **Activate** to create the background cron job
- Use **Run Now** for an immediate manual refresh

If the spreadsheet has **Input Parameters** (see below), their current
values are substituted into pivot domains before each refresh cycle.

## KPI Alerts

Click **Alerts** on the spreadsheet form to define threshold watches:

- Specify a **cell reference** (e.g. ``E8``) and **sheet name**
- Set the **operator** and **threshold** value
- Choose **edge** mode (notify once when the condition becomes true) or
  **level** mode (notify every evaluation cycle while true)
- Add notification partners

Alerts are evaluated by a shared cron job. Use **Evaluate Now** for
immediate checking, or **Reset State** to allow an edge alert to re-fire.

## What-If Scenarios

Click **Scenarios** on the spreadsheet form:

- Create named scenarios with cell override values in JSON format:
  ``{"B3": 125000, "Sheet1!C5": 0.15}``
- Mark one scenario as the **Base Case** for comparison
- **Apply to Copy** creates a new spreadsheet with the overrides baked in
- **Export Comparison** shows a side-by-side table of base vs. override values

## Input Parameters

Click **Input Parameters** to register named cells:

- Each parameter has a **name** (e.g. ``start_date``), a **cell reference**
  (e.g. ``Parameters!B2``), and an optional description
- Parameter values are synced from the spreadsheet cell content
- During scheduled refresh, pivot domains containing ``%(start_date)s``
  tokens are automatically substituted with the current parameter value

## Cell Writeback

Enable **Writeback** on the spreadsheet form to allow direct edits to Odoo
records from list-view cells:

- Edits are validated for field writeability and user permissions
- Each write creates an audit log entry (model, record, field, old/new value)
- Use **Rollback** on any log entry to restore the previous value
- The full audit trail is accessible from the **Writeback Log** button

## Email Subscriptions

Click **Subscriptions** to set up periodic email digests:

- Each partner gets one subscription per spreadsheet
- Choose **daily**, **weekly**, or **monthly** frequency
- Optionally include a summary of pivot data in the email body

## Customising Email Templates

Alert notifications, subscription digests, and refresh summaries are
rendered with QWeb templates that can be overridden or customised:

- **Settings > Technical > Views**, search for ``spreadsheet.alert.notification``,
  ``spreadsheet.subscription.digest``, or ``spreadsheet.refresh.notification``
- Inherit the template in a custom module using standard ``<xpath>`` overrides

## XLSX Export

Click **Export XLSX** on the spreadsheet form to download a ``.xlsx`` file:

- Static cell content is rendered on the original sheets
- Each pivot gets a dedicated sheet with fresh data from the database
- Headers and totals are styled for readability
