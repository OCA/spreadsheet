import {_t} from "@web/core/l10n/translation";

function targetKey({chain, selectors}) {
    const parts = Object.keys(selectors || {})
        .sort()
        .map((segment) => `${segment}=${selectors[segment]}`);
    return `${chain}#${parts.join(",")}`;
}

export function collectFieldLinks(model) {
    const mappings = [];
    const seen = {};
    const duplicates = new Set();
    for (const [position, fieldMapping] of model.getters.getAllFieldMappings()) {
        if (!fieldMapping.chain) {
            continue;
        }
        const cell = model.getters.getEvaluatedCell(position);
        if (cell && cell.type === "error") {
            continue;
        }
        const isEmpty = !cell || cell.type === "empty" || cell.value === "";
        const key = targetKey(fieldMapping);
        const ref = model.getters.getRangeString(
            model.getters.getRangeFromZone(position.sheetId, {
                left: position.col,
                right: position.col,
                top: position.row,
                bottom: position.row,
            }),
            position.sheetId
        );
        if (seen[key]) {
            duplicates.add(key);
        }
        seen[key] = ref;
        mappings.push({
            key,
            ref,
            chain: fieldMapping.chain,
            selectors: fieldMapping.selectors,
            value: isEmpty ? null : cell.value,
        });
    }
    const errors = [...duplicates].map((key) => {
        const refs = mappings.filter((m) => m.key === key).map((m) => m.ref);
        return _t("Several cells target the same field: %s", refs.join(", "));
    });
    return {mappings, errors};
}
