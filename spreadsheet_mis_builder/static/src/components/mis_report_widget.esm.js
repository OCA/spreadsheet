import {MisReportWidget} from "@mis_builder/components/mis_report_widget.esm";
import {patch} from "@web/core/utils/patch";

patch(MisReportWidget.prototype, {
    async exportSpreadsheet() {
        const action = await this.orm.call(
            "mis.report.instance",
            "action_export_spreadsheet",
            [this._instanceId()],
            {context: this.context}
        );
        this.action.doAction(action);
    },
});
