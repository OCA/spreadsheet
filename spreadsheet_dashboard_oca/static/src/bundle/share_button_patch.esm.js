import {SpreadsheetShareButton} from "@spreadsheet/components/share_button/share_button";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

import {ShareManageDialog} from "./share_manage/share_manage_dialog.esm";

const MANAGE_SHARES = _t("Manage shares");

patch(SpreadsheetShareButton.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.isDashboard = Boolean(this.env.services.spreadsheet_dashboard_loader);
    },
    onManageShares() {
        if (!this.isDashboard) {
            return;
        }
        const dashboard =
            this.env.services.spreadsheet_dashboard_loader.getActiveDashboard();
        if (!dashboard) {
            return;
        }
        this.dialog.add(ShareManageDialog, {
            dashboardId: dashboard.data.id,
            title: `${dashboard.data.name} - ${MANAGE_SHARES}`,
        });
    },
});
