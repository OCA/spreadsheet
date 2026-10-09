This module allows linking spreadsheet calculators to quotation templates
in Odoo. When a sale order is created from a template that has a
calculator, a copy of the spreadsheet is automatically assigned to the
order with a pre-configured global filter so the ODOO.LIST formulas
display only that order's lines.

The spreadsheet calculator is built on top of ``spreadsheet_oca`` and
uses ODOO.LIST formulas to display sale order line data (product,
quantity, unit price, etc.). Users can add custom formulas, calculations,
and charts to build complex pricing logic.

A **Field Sync** side panel lets users map spreadsheet columns to
sale order line fields. This column-based approach is more intuitive
than cell-by-cell mapping and makes it easy to push calculated values
back to the sale order.
