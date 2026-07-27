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

## **Email a spreadsheet digest on a schedule**

Go to 'Spreadsheet \> Configuration \> Subscriptions' and add one per person
who should receive a spreadsheet by email.

- Pick the **Subscriber** and how often they should hear from you.
- **Include Pivot Data** attaches a live summary of every Odoo pivot in the
  workbook, recomputed at send time rather than reusing stale saved values.
- **Run As** decides whose permissions the figures are computed with; it
  defaults to you. A subscriber therefore never receives numbers that this
  user could not read themselves.

A single scheduled action wakes daily and sends whichever digests are due, so
adding subscribers does not add scheduled actions. **Send Now** delivers one
immediately without waiting for the schedule.
