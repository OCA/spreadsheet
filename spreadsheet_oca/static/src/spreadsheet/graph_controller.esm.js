import {GraphRenderer} from "@web/views/graph/graph_renderer";

import {patch} from "@web/core/utils/patch";

patch(GraphRenderer.prototype, {
    onSpreadsheetButtonClicked() {
        this.actionService.doAction(
            "spreadsheet_oca.spreadsheet_spreadsheet_import_act_window",
            {
                additionalContext: {
                    default_name: this.model.metaData.title,
                    default_datasource_name: this.model.metaData.title,
                    default_import_data: {
                        mode: "graph",
                        metaData: this.model.metaData,
                        searchParams: {
                            ...this.model.searchParams,
                            domain: this.env.searchModel.domainString,
                        },
                    },
                },
            }
        );
    },
});
