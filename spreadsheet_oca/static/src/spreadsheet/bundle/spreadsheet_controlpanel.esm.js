/** @odoo-module **/

import {Component} from "@odoo/owl";
import {ControlPanel} from "@web/search/control_panel/control_panel";

const {useState} = owl;

export class SpreadsheetName extends Component {
    setup() {
        this.state = useState({
            name: this.props.name,
        });
    }
    _onNameChanged(ev) {
        if (ev.target.value) {
            this.env.saveRecord({name: ev.target.value});
        }
        this.state.name = ev.target.value;
    }
}
SpreadsheetName.template = "spreadsheet_oca.SpreadsheetName";

export class SpreadsheetControlPanel extends ControlPanel {}
SpreadsheetControlPanel.template = "spreadsheet_oca.SpreadsheetControlPanel";
SpreadsheetControlPanel.props = {
    ...ControlPanel.props,
    record: Object,
};
SpreadsheetControlPanel.components = {
    SpreadsheetName,
};
