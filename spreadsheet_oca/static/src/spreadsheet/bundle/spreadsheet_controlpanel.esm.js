import {Component, proxy, t, useProps} from "@odoo/owl";
import {Breadcrumbs} from "@web/search/breadcrumbs/breadcrumbs";
import {ControlPanel} from "@web/search/control_panel/control_panel";

export class SpreadsheetName extends Component {
    static template = "spreadsheet_oca.SpreadsheetName";
    props = useProps({
        name: t.string(),
        isReadonly: t.boolean(),
        onChanged: t.function().optional(),
    });

    setup() {
        this.state = proxy({
            name: this.props.name,
        });
    }
    _onNameChanged(ev) {
        if (this.props.isReadonly) {
            return;
        }
        if (ev.target.value) {
            this.env.saveRecord({name: ev.target.value});
        }
        this.state.name = ev.target.value;
        if (this.props.onChanged) {
            this.props.onChanged(ev);
        }
    }
}

export class SpreadsheetBreadcrumbs extends Breadcrumbs {
    static template = "spreadsheet_oca.Breadcrumbs";
    static components = {
        ...Breadcrumbs.components,
        SpreadsheetName,
    };
    props = useProps({
        breadcrumbs: t.array(),
        record: t.object(),
        slots: t.object().optional(),
    });
}

export class SpreadsheetControlPanel extends ControlPanel {
    static template = "spreadsheet_oca.SpreadsheetControlPanel";
    static components = {
        ...ControlPanel.components,
        SpreadsheetBreadcrumbs,
    };
    props = useProps({
        display: t.object().optional({actions: true, buttons: true}),
        record: t.object(),
    });
}
