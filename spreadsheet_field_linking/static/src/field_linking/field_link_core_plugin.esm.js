import {CommandResult, helpers} from "@odoo/o-spreadsheet";
import {OdooCorePlugin} from "@spreadsheet/plugins";

const {positionToZone, toCartesian, toXC} = helpers;

function sameSelectors(a = {}, b = {}) {
    const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
    for (const key of keys) {
        if (String(a[key]) !== String(b[key])) {
            return false;
        }
    }
    return true;
}

export class FieldLinkCorePlugin extends OdooCorePlugin {
    static getters = [
        "getAllFieldMappings",
        "getFieldMapping",
        "getFieldMappingsInZone",
        "getFieldLinkContext",
    ];

    fieldMappings = {};

    constructor(config) {
        super(config);
        const custom = config.custom || {};
        this.linkContext = custom.linkContext || {
            isLinkable: false,
            writable: false,
            model: false,
            resId: false,
            recordName: false,
            spreadsheetId: custom.linkResId || false,
        };
        if (!custom.linkContext && custom.linkResId && custom.orm) {
            custom.orm
                .call("spreadsheet.spreadsheet", "get_linking_context", [
                    [custom.linkResId],
                ])
                .then((context) => Object.assign(this.linkContext, context))
                .catch(() => {
                    // Best effort: keep the default not-linked context.
                });
        }
    }

    getFieldLinkContext() {
        return this.linkContext;
    }

    allowDispatch(cmd) {
        switch (cmd.type) {
            case "MAP_FIELD": {
                const current = this.getFieldMapping(cmd);
                if (
                    current &&
                    current.chain === cmd.chain &&
                    sameSelectors(current.selectors, cmd.selectors)
                ) {
                    return CommandResult.NoChanges;
                }
                break;
            }
            case "UNMAP_FIELDS":
                if (this.getFieldMappingsInZone(cmd.sheetId, cmd.zone).length === 0) {
                    return CommandResult.NoChanges;
                }
                break;
        }
        return CommandResult.Success;
    }

    handle(cmd) {
        switch (cmd.type) {
            case "MAP_FIELD": {
                const selectors = {};
                for (const [segment, position] of Object.entries(cmd.selectors || {})) {
                    selectors[segment] = Math.max(1, position);
                }
                this.history.update("fieldMappings", cmd.sheetId, cmd.col, cmd.row, {
                    chain: cmd.chain,
                    selectors,
                });
                break;
            }
            case "UNMAP_FIELDS":
                for (let col = cmd.zone.left; col <= cmd.zone.right; col++) {
                    for (let row = cmd.zone.top; row <= cmd.zone.bottom; row++) {
                        this.history.update(
                            "fieldMappings",
                            cmd.sheetId,
                            col,
                            row,
                            undefined
                        );
                    }
                }
                break;
        }
    }

    adaptRanges({applyChange}) {
        const removed = [];
        const moved = [];
        for (const [position, fieldMapping] of this.getAllFieldMappings()) {
            const change = applyChange(
                this.getters.getRangeFromZone(
                    position.sheetId,
                    positionToZone(position)
                )
            );
            if (change.changeType === "REMOVE") {
                removed.push(position);
            } else if (change.changeType !== "NONE") {
                removed.push(position);
                moved.push([
                    {
                        sheetId: position.sheetId,
                        col: change.range.zone.left,
                        row: change.range.zone.top,
                    },
                    fieldMapping,
                ]);
            }
        }
        for (const {sheetId, col, row} of removed) {
            this.history.update("fieldMappings", sheetId, col, row, undefined);
        }
        for (const [{sheetId, col, row}, fieldMapping] of moved) {
            this.history.update("fieldMappings", sheetId, col, row, fieldMapping);
        }
    }

    getFieldMapping({sheetId, col, row}) {
        return this.fieldMappings[sheetId]?.[col]?.[row];
    }

    getAllFieldMappings() {
        const result = new Map();
        for (const sheetId in this.fieldMappings) {
            for (const col in this.fieldMappings[sheetId]) {
                for (const row in this.fieldMappings[sheetId][col]) {
                    const fieldMapping = this.fieldMappings[sheetId][col][row];
                    if (fieldMapping) {
                        result.set(
                            {sheetId, col: Number(col), row: Number(row)},
                            fieldMapping
                        );
                    }
                }
            }
        }
        return result;
    }

    getFieldMappingsInZone(sheetId, zone) {
        const result = [];
        for (let col = zone.left; col <= zone.right; col++) {
            for (let row = zone.top; row <= zone.bottom; row++) {
                const fieldMapping = this.getFieldMapping({sheetId, col, row});
                if (fieldMapping) {
                    result.push(fieldMapping);
                }
            }
        }
        return result;
    }

    export(data) {
        for (const [position, fieldMapping] of this.getAllFieldMappings()) {
            const sheet = data.sheets.find((s) => s.id === position.sheetId);
            if (!sheet) {
                continue;
            }
            sheet.fieldMappings ??= {};
            sheet.fieldMappings[toXC(position.col, position.row)] = fieldMapping;
        }
    }

    import(data) {
        for (const sheet of data.sheets) {
            if (!sheet.fieldMappings) {
                continue;
            }
            for (const [xc, fieldMapping] of Object.entries(sheet.fieldMappings)) {
                const {col, row} = toCartesian(xc);
                this.history.update("fieldMappings", sheet.id, col, row, fieldMapping);
            }
        }
    }
}
