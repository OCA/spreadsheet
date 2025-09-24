import {PivotRenderer} from "@web/views/pivot/pivot_renderer";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(PivotRenderer.prototype, {
    isComparingInfo() {
        return Boolean(this.model.searchParams.comparison);
    },
    containsDuplicatedGroupBys() {
        const colGroupBys = new Set(
            this.model.metaData.colGroupBys
                .concat(this.model.metaData.expandedColGroupBys)
                .map((el) => el.split(":")[0])
        );
        const rowGroupBys = new Set(
            this.model.metaData.rowGroupBys
                .concat(this.model.metaData.expandedRowGroupBys)
                .map((el) => el.split(":")[0])
        );
        return Boolean(colGroupBys.intersection(rowGroupBys).size);
    },
    containsColGroupBys() {
        const colGroupBys = new Set(
            this.model.metaData.colGroupBys
                .concat(this.model.metaData.expandedColGroupBys)
                .map((el) => el.split(":")[0])
        );
        return Boolean(colGroupBys.size);
    },
    disableSpreadsheetInsertion() {
        return (
            !this.model.hasData() ||
            !this.model.metaData.activeMeasures.length ||
            this.containsDuplicatedGroupBys() ||
            this.isComparingInfo()
        );
    },
    getSpreadsheetInsertionTooltip() {
        var message = _t("Add to spreadsheet");
        if (this.containsDuplicatedGroupBys()) {
            message = _t("Duplicated groupbys in pivot are not supported");
        } else if (this.isComparingInfo()) {
            message = _t("Comparisons in pivot are not supported");
        }
        return message;
    },
    onSpreadsheetButtonClicked() {
        this.actionService.doAction(
            "spreadsheet_oca.spreadsheet_spreadsheet_import_act_window",
            {
                additionalContext: {
                    default_name: this.model.metaData.title,
                    default_datasource_name: this.model.metaData.title,
                    default_can_be_dynamic: false,
                    default_can_have_dynamic_cols: false,
                    // Default_can_be_dynamic: true,
                    // default_can_have_dynamic_cols: this.containsColGroupBys(),
                    default_import_data: {
                        mode: "pivot",
                        metaData: JSON.parse(JSON.stringify(this.model.metaData)),
                        searchParams: JSON.parse(
                            JSON.stringify(this.model.searchParams)
                        ),
                    },
                },
            }
        );
    },
});
