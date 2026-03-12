## **Create a new spreadsheet**

- Go to 'Spreadsheet' menu
- Click on 'Create'
- Put a name, then click on the "Edit" button

![](../static/description/spreadsheet_create.png)

- At this point you switch to spreadsheet editing mode. The editor is
  named `o-spreadsheet` and looks like another common spreadsheet web
  editors. (OnlyOffice, Ethercalc, Google Sheets (non-free)).

![](../static/description/spreadsheet_edit.png)

- You can use common functions `SUM()`, `AVERAGE()`, etc. in the cells.
  For a complete list of functions and their syntax, Refer to the
  documentation <https://github.com/odoo/o-spreadsheet/> or go to
  <https://odoo.github.io/o-spreadsheet/> and click on "Insert \>
  Function".

![](../static/description/o-spreadsheet.png)

- Note: Business Odoo module can add "business functions". This is
  currently the case for the accounting module, which adds the following
  features:

  > - `ODOO.CREDIT(account_codes, date_range)`: Get the total credit for
  >   the specified account(s) and period.
  > - `ODOO.DEBIT(account_codes, date_range)`: Get the total debit for
  >   the specified account(s) and period.
  > - `ODOO.BALANCE(account_codes, date_range)`: Get the total balance
  >   for the specified account(s) and period.
  > - `ODOO.FISCALYEAR.START(day)`: Returns the starting date of the
  >   fiscal year encompassing the provided date.
  > - `ODOO.FISCALYEAR.END(day)`: Returns the ending date of the fiscal
  >   year encompassing the provided date.
  > - `ODOO.ACCOUNT.GROUP(type)`: Returns the account ids of a given
  >   group where type should be a value of the `account_type` field of
  >   `account.account` model. (`income`, `asset_receivable`, etc.)

## **Get notified when a KPI crosses a threshold**

- Go to 'Spreadsheet \> Configuration \> KPI Alerts' and click **New**.
- Pick the spreadsheet, the **Cell Reference** to watch (e.g. `C3`) and,
  if the workbook has several sheets, the **Sheet**.
- Choose a comparison and a **Threshold** — for example `<` and `0.15`.
- **Run As** decides whose permissions the evaluation uses; it defaults to you.
- **Trigger Mode** controls repetition:
  - *Edge* notifies once, when the condition first becomes true. Use this for
    "tell me when we fall behind".
  - *Level* notifies on every cycle while the condition holds. Use this for
    "keep reminding me until it is fixed".
- Add partners under **Notify Partners** to have them emailed as well.

A single scheduled action wakes hourly and evaluates every active alert, so
adding alerts does not add scheduled actions. Use **Evaluate Now** to test an
alert immediately, and **Reset State** to let an *edge* alert fire again without
waiting for the value to recover first.

The watched cell must hold a number. A cell that is missing, on a sheet that
does not exist, or holding text is logged as a warning and the alert never
fires.
