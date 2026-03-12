## Architecture

The module is built on the ``o-spreadsheet`` OWL component bundled with
Odoo CE. Server-side features are implemented as standard Odoo models with
cron jobs, controllers, and security rules.

### Key Files

- ``models/spreadsheet_spreadsheet.py`` — main document model with pivot
  data endpoint, XLSX export, and writeback rollback
- ``models/spreadsheet_oca_revision.py`` — collaborative editing revisions
- ``models/cell_ref.py`` — cell reference parsing and value reading utilities
- ``models/pivot_data.py`` — server-side pivot computation via ``read_group``
- ``models/spreadsheet_xlsx_export.py`` — XLSX rendering with ``openpyxl``
- ``controllers/`` — JSON endpoints for writeback and input parameters

### Adding Custom Business Functions

To add spreadsheet functions from another module, extend the JS function
registry. See the accounting functions in Odoo CE as a reference:
<https://github.com/odoo/odoo/blob/18.0/addons/spreadsheet_account/static/src/accounting_functions.js>

### Pivot Data Format

Pivot definitions in the spreadsheet JSON use this structure:

```json
{
  "type": "ODOO",
  "model": "res.partner",
  "domain": [["active", "=", true]],
  "measures": [{"id": "__count", "fieldName": "__count"}],
  "rows": [{"fieldName": "country_id", "order": "desc"}],
  "columns": [{"fieldName": "is_company"}]
}
```

The measure ID format is ``fieldName:aggregator`` for real fields (e.g.
``amount_total:sum``) or just ``fieldName`` for virtual fields like
``__count``. The ``__count`` measure must **not** include an aggregator
suffix. Formulas must match the measure ID:
``=PIVOT.VALUE(1,"__count","#country_id",1)``.

### Running Tests

```bash
# Python unit tests
odoo -d test_db -i spreadsheet_oca --test-enable --stop-after-init

# With pytest (if pytest-odoo is installed)
pytest odoo/custom/src/spreadsheet/spreadsheet_oca/tests/
```
