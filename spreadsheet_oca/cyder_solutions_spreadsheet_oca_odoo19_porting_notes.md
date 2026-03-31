# Odoo 19.0 Port — `spreadsheet_oca` & `spreadsheet_dashboard_oca`

**Author:** Cyder Solutions  
**Date:** March 2026  
**Base version ported:** `spreadsheet_oca` 19.0.1.0.3 / `spreadsheet_dashboard_oca` 19.0.1.0.0  
**Target:** Odoo 19.0 Community Edition  

---

## Overview

This document records all breaking changes encountered and fixes applied when porting `spreadsheet_oca` and `spreadsheet_dashboard_oca` to run against Odoo 19.0 Community Edition. The changes are grouped by module and file. All fixes were verified against a running Odoo 19.0 Community instance.

---

## Module: `spreadsheet_oca`

### `security/security.xml`

**Issue 1:** `category_id` field removed from `res.groups` in Odoo 19.

```xml
<!-- REMOVE these lines from group_user and group_manager records -->
<field name="category_id" ref="module_category_spreedsheet" />
```

**Issue 2:** `users` field removed from `res.groups` in Odoo 19.

```xml
<!-- REMOVE this from group_manager record -->
<field name="users" eval="[(4, ref('base.user_root')), (4, ref('base.user_admin'))]" />
```

**Issue 3:** `groups_id` renamed to `group_ids` on `res.users` — affects domain expressions in `ir.rule` records.

```xml
<!-- BEFORE -->
['|', ('contributor_ids','=', user.id), ('contributor_group_ids','in', user.groups_id.ids)]
<!-- AFTER -->
['|', ('contributor_ids','=', user.id), ('contributor_group_ids','in', user.group_ids.ids)]
```

---

### `views/spreadsheet_spreadsheet.xml`

**Issue:** `groups_id` renamed to `group_ids` on `ir.ui.menu` in Odoo 19.

```xml
<!-- BEFORE -->
<field name="groups_id" eval="[(4, ref('spreadsheet_oca.group_user'))]" />
<!-- AFTER -->
<field name="group_ids" eval="[(4, ref('spreadsheet_oca.group_user'))]" />
```

---

### `static/src/spreadsheet/bundle/filter.esm.js`

**Issue 1:** `globalFiltersFieldMatchers` removed from `global_filters_core_plugin`. Replaced by `globalFieldMatchingRegistry` in `global_filters/helpers`. The registry API also changed — all matcher methods now take `getters` as their first argument.

```javascript
// BEFORE
import {globalFiltersFieldMatchers} from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";
// ...
for (var [objectType, objectClass] of Object.entries(globalFiltersFieldMatchers)) {
    for (const objectId of objectClass.getIds()) {
        var fields = objectClass.getFields(objectId);
        name: objectClass.getDisplayName(objectId),
        tag: await objectClass.getTag(objectId),
        fieldMatch: objectClass.getFieldMatching(objectId, this.props.filter.id),
        model: objectClass.getModel(objectId),

// AFTER
import {globalFieldMatchingRegistry} from "@spreadsheet/global_filters/helpers";
// ...
const getters = this.env.model.getters;
for (const objectType of globalFieldMatchingRegistry.getKeys()) {
    const objectClass = globalFieldMatchingRegistry.get(objectType);
    for (const objectId of objectClass.getIds(getters)) {
        var fields = objectClass.getFields(getters, objectId);
        name: objectClass.getDisplayName(getters, objectId),
        tag: await objectClass.getTag(getters, objectId),
        fieldMatch: objectClass.getFieldMatching(getters, objectId, this.props.filter.id),
        model: objectClass.getModel(getters, objectId),
```

**Issue 2:** `RELATIVE_DATE_RANGE_TYPES` removed from `@spreadsheet/helpers/constants`. Renamed to `RELATIVE_PERIODS` in `@spreadsheet/global_filters/helpers`.

```javascript
// BEFORE
import {RELATIVE_DATE_RANGE_TYPES} from "@spreadsheet/helpers/constants";
this.relativeDateRangeTypes = RELATIVE_DATE_RANGE_TYPES;

// AFTER
import {RELATIVE_PERIODS} from "@spreadsheet/global_filters/helpers";
this.relativeDateRangeTypes = RELATIVE_PERIODS;
```

**Issue 3:** `topbarMenuRegistry.add("file", ...)` — the `"file"` menu entry is already registered by the Odoo 19 community `spreadsheet` module. Remove the duplicate registration.

```javascript
// REMOVE this line entirely
topbarMenuRegistry.add("file", {name: _t("File"), sequence: 10});
```

**Issue 4:** `topbarMenuRegistry.addChild("settings", ...)` — the `"settings"` child is also already registered. Remove it.

```javascript
// REMOVE this block entirely
topbarMenuRegistry.addChild("settings", ["file"], {
    name: _t("Settings"),
    sequence: 100,
    execute: (env) => env.openSidePanel("Settings"),
    icon: "o-spreadsheet-Icon.COG",
});
```

---

### `static/src/spreadsheet/bundle/spreadsheet_renderer.esm.js`

**Issue:** `loadSpreadsheetDependencies` and its module `@spreadsheet/assets_backend/helpers` were removed in Odoo 19. Replaced by `loadBundle` from `@web/core/assets`.

```javascript
// BEFORE
import {loadSpreadsheetDependencies} from "@spreadsheet/assets_backend/helpers";
// ...
await loadSpreadsheetDependencies();

// AFTER
import {loadBundle} from "@web/core/assets";
// ...
await loadBundle("spreadsheet.o_spreadsheet");
```

---

### `static/src/spreadsheet/bundle/spreadsheet_action.esm.js`

**Issue:** Odoo 19 raises an error if a registry key already exists without explicit `force: true`. The action `"action_spreadsheet_oca"` is first registered by the lazy loader in `web.assets_backend`, so the bundle registration must use `force: true`.

```javascript
// BEFORE
actionRegistry.add("action_spreadsheet_oca", ActionSpreadsheetOca, {
    force: true,
});
// The OCA module originally had force: true but it was removed during porting
// attempts — it must be restored.

// CORRECT
actionRegistry.add("action_spreadsheet_oca", ActionSpreadsheetOca, { force: true });
```

---

### `static/src/spreadsheet/bundle/odoo_panels.esm.js`

**Issue:** `chartSubtypeRegistry` entries for `odoo_line`, `odoo_stacked_line`, `odoo_area`, `odoo_stacked_area`, `odoo_bar`, `odoo_stacked_bar`, and `odoo_pie` are already registered by the Odoo 19 community `spreadsheet` module. Remove all `chartSubtypeRegistry.add(...)` calls from this file — they are no longer needed.

The `chartSidePanelComponentRegistry` entries (`odoo_line`, `odoo_bar`, `odoo_pie`) are unique to the OCA module and should be kept.

---

### `static/src/spreadsheet/bundle/filter_panel_datasources.esm.js`

**Issue:** `pivotSidePanelRegistry.add("ODOO", ...)` — the `"ODOO"` entry is already registered by the Odoo 19 community `spreadsheet` module. Add `{ force: true }` to override it.

```javascript
// BEFORE
pivotSidePanelRegistry.add("ODOO", {
    editor: PivotPanel,
});

// AFTER
pivotSidePanelRegistry.add("ODOO", {
    editor: PivotPanel,
}, { force: true });
```

---

## Module: `spreadsheet_dashboard_oca`

No changes were required to `spreadsheet_dashboard_oca` itself. All issues were in the base `spreadsheet_oca` module.

---

## Summary of Changed Files

| Module | File | Change Type |
|--------|------|-------------|
| `spreadsheet_oca` | `security/security.xml` | Removed `category_id`, `users` from groups; renamed `groups_id` → `group_ids` in rules |
| `spreadsheet_oca` | `views/spreadsheet_spreadsheet.xml` | Renamed `groups_id` → `group_ids` on menu record |
| `spreadsheet_oca` | `bundle/filter.esm.js` | Updated `globalFiltersFieldMatchers` API; fixed `RELATIVE_DATE_RANGE_TYPES`; removed duplicate menu registrations |
| `spreadsheet_oca` | `bundle/spreadsheet_renderer.esm.js` | Replaced `loadSpreadsheetDependencies` with `loadBundle` |
| `spreadsheet_oca` | `bundle/spreadsheet_action.esm.js` | Restored `force: true` on `actionRegistry.add` |
| `spreadsheet_oca` | `bundle/odoo_panels.esm.js` | Removed duplicate `chartSubtypeRegistry` entries |
| `spreadsheet_oca` | `bundle/filter_panel_datasources.esm.js` | Added `force: true` to `pivotSidePanelRegistry.add` |

---

## Notes for OCA Contribution

When submitting these changes as a PR to the OCA/spreadsheet repository:

- The Python/XML changes are clean and straightforward — standard Odoo 19 API removals.
- The JS changes to `filter.esm.js` involve the most significant API change (`globalFiltersFieldMatchers` → `globalFieldMatchingRegistry` with new method signatures). This should be tested against actual filter panel behaviour with live pivot and list data sources.
- The duplicate registry entries in `odoo_panels.esm.js` and `filter.esm.js` suggest the OCA module may have been developed against an Odoo version where these entries were not yet present in the community spreadsheet module. As Odoo 19 includes them natively, the OCA module should check before registering rather than relying on `force: true` as a blanket fix.
- The `loadSpreadsheetDependencies` removal is a clean API change — `loadBundle` is the documented replacement.
