This module adds a **quote calculator** to quotations: an Odoo spreadsheet, attached to the order, whose results are written straight onto the order lines.

Many quotes depend on a calculation — square metres, weights, tiered discounts, material breakdowns — that usually lives in a separate spreadsheet and is copied back onto the order by hand. This module brings that spreadsheet inside Odoo: you build the calculation once with ordinary formulas, point its result cells at the order-line fields they should feed (unit price, quantity, discount, description...), and push the computed values onto the lines in a single click.

The usual way is to prepare the calculator once on a **quotation template** and let every quote made from it reuse it, but you can also attach one straight to a single order. Either way each quote gets its own private copy, so a salesperson can adjust their own inputs without ever touching the shared original.

The sync is one-way (spreadsheet → order lines) and triggered by hand, so it never disturbs normal quoting and the spreadsheet stays completely free-form.

It builds on **spreadsheet_field_linking**, which provides the cell-to-field linking; this module adds the sale-specific tools: the template calculator, the per-quote copy, and the smart button on the order.
