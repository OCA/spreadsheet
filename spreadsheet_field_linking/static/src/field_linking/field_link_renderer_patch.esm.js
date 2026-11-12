import {SpreadsheetRenderer} from "@spreadsheet_oca/spreadsheet/bundle/spreadsheet_renderer.esm";
import {patch} from "@web/core/utils/patch";

patch(SpreadsheetRenderer.prototype, {
    setup() {
        super.setup();
        if (this.env.linkModelHolder) {
            this.env.linkModelHolder.model = this.spreadsheet_model;
        }
    },

    getExtraModelCustom() {
        return {...super.getExtraModelCustom(), linkResId: this.props.res_id};
    },
});
