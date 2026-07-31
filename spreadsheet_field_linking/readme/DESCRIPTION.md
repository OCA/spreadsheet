This module turns an Odoo spreadsheet into a tool that can be used to push data to a record.

You link a spreadsheet to a record (a sale order, a project, a partner...), point some of its cells at the fields of that record, and then write the values you computed in the spreadsheet back onto the record in one click.

A typical use is building a pricing or estimation sheet: you do the maths in the spreadsheet, and the results land on the right fields of the order without any copy-paste. Cells can target a field of the linked record, a field of a related record, or a field on the lines of the record.

The links are stored inside the spreadsheet itself, so they are kept when the file is saved and reopened, and they follow their cells when rows are moved.

This is a foundation module: it adds the linking tools to every Odoo spreadsheet but does not, by itself, tie any particular business document to a spreadsheet. Other modules build on it could offer ready-made spreadsheets for their own models.
