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

## **Schedule an automatic data refresh**

A spreadsheet that contains `=PIVOT()` formulas can be re-computed on a
schedule, with the resulting tables posted to its Chatter.

- Open a spreadsheet, then click the **Schedules** smart button (or go to
  'Spreadsheet \> Configuration \> Refresh Schedules').
- Click **New**, pick the spreadsheet, and set how often it should run —
  for example every `1` `Week(s)`.
- Optionally add partners under **Notify Partners**; they receive the same
  summary by email.
- **Run As** decides whose permissions the refresh uses. It defaults to you.
- Use **Pause** to stop a schedule without losing its configuration,
  **Activate** to resume it, and **Run Now** to refresh immediately.

A single scheduled action ('Spreadsheet: Scheduled Data Refresh') wakes hourly
and refreshes whichever schedules are due, so adding schedules does not add
scheduled actions.

Each run reads every Odoo pivot defined in the spreadsheet, recomputes it
server-side, and posts one rendered table per pivot to the spreadsheet's
Chatter, along with the total record count. **Last Run** records when it
last executed.

Note that the pivots are computed with the permissions of the schedule's
**Run As** user — not the scheduler's — so a summary never exposes records
that user could not read themselves.
