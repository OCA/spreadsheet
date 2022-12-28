/** @odoo-module **/

import {_lt, _t} from "web.core";
import {Component} from "@odoo/owl";
import {ControlPanel} from "@web/search/control_panel/control_panel";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

const {useState} = owl;
const {topbarMenuRegistry} = spreadsheet.registries;

topbarMenuRegistry.add("file", {name: _t("File"), sequence: 10});
topbarMenuRegistry.addChild("save", ["file"], {
    name: _lt("Save"),
    // Description: "Ctrl+S", // This is not working, so removing it from the view for now...
    sequence: 10,
    action: (env) => env.saveSpreadsheet(),
});
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
