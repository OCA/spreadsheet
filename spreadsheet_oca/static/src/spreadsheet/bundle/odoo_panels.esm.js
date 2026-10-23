import * as spreadsheet from "@odoo/o-spreadsheet";
import {Component, onWillStart, useProps} from "@odoo/owl";
import {Domain} from "@web/core/domain";
import {DomainSelector} from "@web/core/domain_selector/domain_selector";
import {useService} from "@web/core/utils/hooks";

const {chartDataSourceSidePanelComponentRegistry} = spreadsheet.registries;

/**
 * Data source section of the chart side panel for the charts coming from an
 * Odoo graph view (charts with an "odoo" data source).
 */
export class OdooChartDataSourcePanel extends Component {
    static template = "spreadsheet_oca.OdooChartDataSourcePanel";
    static components = {DomainSelector};
    props = useProps();

    setup() {
        this.orm = useService("orm");
        onWillStart(async () => {
            const result = await this.orm.call("ir.model", "display_name_for", [
                [this.resModel],
            ]);
            this.modelLabel = (result[0] && result[0].display_name) || "";
        });
    }
    get resModel() {
        return this.props.dataSource.metaData.resModel;
    }
    get domain() {
        return new Domain(this.props.dataSource.searchParams.domain).toString();
    }
}

chartDataSourceSidePanelComponentRegistry.add("odoo", OdooChartDataSourcePanel);
