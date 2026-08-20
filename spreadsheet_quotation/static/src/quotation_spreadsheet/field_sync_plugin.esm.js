/** @odoo-module **/

import {CorePlugin, coreTypes, registries} from "@odoo/o-spreadsheet";
import {_t} from "@web/core/l10n/translation";

const {corePluginRegistry, topbarMenuRegistry} = registries;

coreTypes.add("UPDATE_FIELD_SYNC_CONFIG");
coreTypes.add("ADD_FIELD_SYNC_MAPPING");
coreTypes.add("REMOVE_FIELD_SYNC_MAPPING");

/**
 * Plugin that stores field-sync configuration in the spreadsheet data.
 *
 * The configuration maps spreadsheet columns to sale.order.line fields,
 * allowing the user to sync computed values back to the sale order.
 *
 * The mappings are stored as a list of {column, field} objects where
 * `column` is the 0-based column index and `field` is the technical
 * field name on sale.order.line.
 */
export class FieldSyncCorePlugin extends CorePlugin {
    static getters = /** @type {const} */ ([
        "getFieldSyncConfig",
        "getFieldSyncMappings",
        "getFieldSyncListId",
    ]);

    constructor(config) {
        super(config);
        this.fieldSyncConfig = {
            listId: "1",
            mappings: [],
        };
    }

    allowDispatch(cmd) {
        switch (cmd.type) {
            case "UPDATE_FIELD_SYNC_CONFIG":
            case "ADD_FIELD_SYNC_MAPPING":
            case "REMOVE_FIELD_SYNC_MAPPING":
                return "Success";
        }
        return "Success";
    }

    handle(cmd) {
        switch (cmd.type) {
            case "UPDATE_FIELD_SYNC_CONFIG":
                this.history.update("fieldSyncConfig", cmd.config);
                break;
            case "ADD_FIELD_SYNC_MAPPING": {
                const mappings = [...this.fieldSyncConfig.mappings, cmd.mapping];
                this.history.update("fieldSyncConfig", {
                    ...this.fieldSyncConfig,
                    mappings,
                });
                break;
            }
            case "REMOVE_FIELD_SYNC_MAPPING": {
                const mappings = this.fieldSyncConfig.mappings.filter(
                    (_, idx) => idx !== cmd.index
                );
                this.history.update("fieldSyncConfig", {
                    ...this.fieldSyncConfig,
                    mappings,
                });
                break;
            }
        }
    }

    getFieldSyncConfig() {
        return this.fieldSyncConfig;
    }

    getFieldSyncMappings() {
        return this.fieldSyncConfig.mappings || [];
    }

    getFieldSyncListId() {
        return this.fieldSyncConfig.listId || "1";
    }

    import(data) {
        if (data.fieldSyncConfig) {
            this.fieldSyncConfig = data.fieldSyncConfig;
        }
    }

    export(data) {
        data.fieldSyncConfig = this.fieldSyncConfig;
    }
}

corePluginRegistry.add("FieldSyncCorePlugin", FieldSyncCorePlugin);

topbarMenuRegistry.addChild("field_sync", ["file"], {
    name: _t("Field Sync"),
    sequence: 80,
    execute: (env) => env.openSidePanel("FieldSyncPanel", {}),
    icon: "o-spreadsheet-Icon.EDIT",
    isVisible: (env) => {
        const listIds = env.model.getters.getListIds();
        return listIds.length > 0;
    },
});
