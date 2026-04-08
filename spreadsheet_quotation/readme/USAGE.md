Setting up a quotation calculator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Go to **Sales > Configuration > Quotation Templates**.
2. Open or create a quotation template.
3. Click **Create Calculator** next to the "Quotation Calculator" field.
4. A wizard will open; set a name and number of initial rows, then click
   **Create Calculator**.
5. The spreadsheet editor opens with a pre-configured list of
   ``sale.order.line`` fields.
6. Customize the spreadsheet: add formulas, charts, or extra columns as
   needed.
7. Save the spreadsheet.

Using the calculator on a sale order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Create a new quotation and select the template that has a calculator.
2. A **Calculator** smart button appears on the sale order form.
3. Click it to open the spreadsheet filtered to the current order's
   lines.
4. Edit values in the spreadsheet.
5. Use **File > Field Sync** to map columns to sale order line fields.
6. Save the spreadsheet from the editor.

Syncing values back to the order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After configuring field sync mappings in the spreadsheet, the mapped
column values can be pushed to the corresponding sale order line fields
when saving the spreadsheet or from the sale order form.
