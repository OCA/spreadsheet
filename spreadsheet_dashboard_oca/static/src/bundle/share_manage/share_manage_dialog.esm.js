import {Component, onWillStart, useState} from "@odoo/owl";
import {CopyButton} from "@web/core/copy_button/copy_button";
import {Dialog} from "@web/core/dialog/dialog";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";

export class ShareManageDialog extends Component {
    static template = "spreadsheet_dashboard_oca.ShareManageDialog";
    static components = {CopyButton, Dialog};
    static props = {
        dashboardId: {type: Number},
        title: {type: String},
        close: {type: Function, optional: true},
    };

    setup() {
        this.copiedText = _t("Copied");
        this.orm = useService("orm");
        this.state = useState({shares: [], revoking: 0});
        onWillStart(async () => {
            await this._loadShares();
        });
    }

    async _loadShares() {
        this.state.shares = await this.orm.call(
            "spreadsheet.dashboard.share",
            "action_get_dashboard_shares",
            [this.props.dashboardId]
        );
    }

    async onRevoke(share) {
        if (this.state.revoking === share.id) {
            return;
        }
        this.state.revoking = share.id;
        try {
            await this.orm.call("spreadsheet.dashboard.share", "action_unshare", [
                [share.id],
            ]);
            this.state.shares = this.state.shares.filter((s) => s.id !== share.id);
            this.env.bus.trigger("dashboards-shares-updated");
        } finally {
            this.state.revoking = 0;
        }
    }
}
