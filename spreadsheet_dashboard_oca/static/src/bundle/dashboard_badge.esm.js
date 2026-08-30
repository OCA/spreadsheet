import {onWillStart, useState} from "@odoo/owl";
import {SpreadsheetDashboardAction} from "@spreadsheet_dashboard/bundle/dashboard_action/dashboard_action";
import {patch} from "@web/core/utils/patch";
import {useBus} from "@web/core/utils/hooks";

patch(SpreadsheetDashboardAction.prototype, {
    setup() {
        super.setup();
        this.shareCounts = useState({});
        onWillStart(async () => {
            await this._loadShareCounts();
        });
        useBus(this.env.bus, "dashboards-shares-updated", () =>
            this._loadShareCounts()
        );
    },
    async _loadShareCounts() {
        try {
            const counts = await this.orm.call(
                "spreadsheet.dashboard.share",
                "action_get_share_counts",
                []
            );
            Object.assign(this.shareCounts, counts);
        } catch {
            // Keep previous counts on failure
        }
    },
    async shareSpreadsheet(data, excelExport) {
        const url = await super.shareSpreadsheet(data, excelExport);
        this.env.bus.trigger("dashboards-shares-updated");
        return url;
    },
});
