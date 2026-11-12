import {coreTypes, registries} from "@odoo/o-spreadsheet";
import {FieldLinkCorePlugin} from "./field_link_core_plugin.esm";
import {FieldLinkSidePanel} from "./field_link_side_panel.esm";
import {ManageLinkedRecordSidePanel} from "./manage_linked_record_side_panel.esm";
import {_t} from "@web/core/l10n/translation";

const {
    corePluginRegistry,
    sidePanelRegistry,
    cellMenuRegistry,
    topbarMenuRegistry,
    inverseCommandRegistry,
} = registries;

const identity = (cmd) => cmd;
const isLinkable = (env) =>
    Boolean(env.model.getters.getFieldLinkContext?.().isLinkable);

const linkActiveCell = (env) => {
    const position = env.model.getters.getActivePosition();
    if (!env.model.getters.getFieldMapping(position)) {
        env.model.dispatch("MAP_FIELD", {
            sheetId: position.sheetId,
            col: position.col,
            row: position.row,
            chain: "",
            selectors: {},
        });
    }
    env.openSidePanel("FieldLinkPanel");
};

coreTypes.add("MAP_FIELD").add("UNMAP_FIELDS");
corePluginRegistry.add("field_link", FieldLinkCorePlugin);
inverseCommandRegistry.add("MAP_FIELD", identity);
inverseCommandRegistry.add("UNMAP_FIELDS", identity);

sidePanelRegistry.add("ManageLinkedRecord", {
    title: _t("Manage linked record"),
    Body: ManageLinkedRecordSidePanel,
});

sidePanelRegistry.add("FieldLinkPanel", {
    title: _t("Link to field"),
    Body: FieldLinkSidePanel,
    computeState(getters, initialProps) {
        const position = getters.getActivePosition();
        return {
            isOpen: Boolean(getters.getFieldMapping?.(position)),
            props: {...initialProps, position},
            key: `${position.sheetId}-${position.col}-${position.row}`,
        };
    },
});

cellMenuRegistry.add("field_link", {
    name: (env) =>
        env.model.getters.getFieldMapping?.(env.model.getters.getActivePosition())
            ? _t("Edit field link")
            : _t("Link to field"),
    icon: "o-spreadsheet-Icon.REFRESH",
    sequence: 200,
    isVisible: (env) => isLinkable(env) && !env.isSmall,
    execute: linkActiveCell,
});

cellMenuRegistry.add("field_link_delete", {
    name: _t("Remove field link"),
    icon: "o-spreadsheet-Icon.TRASH",
    sequence: 201,
    isVisible: (env) => {
        if (!isLinkable(env)) {
            return false;
        }
        const sheetId = env.model.getters.getActiveSheetId();
        return env.model.getters
            .getSelectedZones()
            .some(
                (zone) => env.model.getters.getFieldMappingsInZone(sheetId, zone).length
            );
    },
    execute: (env) => {
        const sheetId = env.model.getters.getActiveSheetId();
        for (const zone of env.model.getters.getSelectedZones()) {
            env.model.dispatch("UNMAP_FIELDS", {sheetId, zone});
        }
    },
});

topbarMenuRegistry.addChild("manage_linked_record", ["file"], {
    name: _t("Manage linked record"),
    icon: "o-spreadsheet-Icon.INSERT_LINK",
    sequence: 90,
    execute: (env) => env.openSidePanel("ManageLinkedRecord"),
});

topbarMenuRegistry.addChild("field_link", ["file"], {
    name: _t("Link to field"),
    icon: "o-spreadsheet-Icon.REFRESH",
    sequence: 100,
    isVisible: isLinkable,
    execute: linkActiveCell,
});
