/** @odoo-module **/

import {_lt, _t} from "web.core";
import {Component} from "@odoo/owl";
import {ControlPanel} from "@web/search/control_panel/control_panel";
import {Field} from "@web/views/fields/field";
import {FormArchParser} from "@web/views/form/form_arch_parser";
import {FormCompiler} from "@web/views/form/form_compiler";
import {FormController} from "@web/views/form/form_controller";
import {RelationalModel} from "@web/views/basic_relational_model";
import {migrate} from "@spreadsheet/o_spreadsheet/migration";
import {registry} from "@web/core/registry";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import {useService} from "@web/core/utils/hooks";

const {Spreadsheet, Model} = spreadsheet;
const {useSubEnv, useState} = owl;
const {topbarMenuRegistry} = spreadsheet.registries;

topbarMenuRegistry.add("file", {name: _t("File"), sequence: 10});
topbarMenuRegistry.addChild("save", ["file"], {
    name: _lt("Save"),
    // Description: "Ctrl+S", // This is not working, so removing it from the view...
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
        this.env.changeNameSpreadsheet(ev.target.value);
        this.state.name = ev.target.value;
    }
}
SpreadsheetName.template = "spreadsheet_oca.SpreadsheetName";
export class SpreadsheetControlPanel extends ControlPanel {}
SpreadsheetControlPanel.template = "spreadsheet_oca.SpreadsheetControlPanel";
SpreadsheetControlPanel.components = {
    SpreadsheetName,
};
export class SpreadsheetRenderer extends Component {
    setup() {
        this.spreadsheet_model = new Model(migrate(this.props.record.data.raw));
        this.field = this.props.record.fields.name;
        this.orm = useService("orm");
        useSubEnv({
            saveSpreadsheet: this.onSpreadsheetSaved.bind(this),
        });
    }
    onSpreadsheetSaved() {
        const data = this.spreadsheet_model.exportData();
        this.props.record.update({raw: data});
        return this.props.record.save({
            noReload: true,
            stayInEdition: true,
            useSaveErrorDialog: true,
        });
    }
}

SpreadsheetRenderer.template = "spreadsheet_oca.SpreadsheetRenderer";
SpreadsheetRenderer.components = {
    Spreadsheet,
    Field,
};
export class SpreadsheetController extends FormController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        useSubEnv({
            changeNameSpreadsheet: this.onSpreadsheetNameChanged.bind(this),
        });
    }
    onSpreadsheetNameChanged(new_name) {
        this.model.root.update({name: new_name});
        this.model.root.save({
            noReload: true,
            stayInEdition: true,
            useSaveErrorDialog: true,
        });
    }
}
export const spreadsheetView = {
    type: "form",
    display_name: "Spreadsheet",
    multiRecord: false,
    searchMenuTypes: [],
    ControlPanel: SpreadsheetControlPanel,
    Controller: SpreadsheetController,
    Renderer: SpreadsheetRenderer,
    ArchParser: FormArchParser,
    Model: RelationalModel,
    Compiler: FormCompiler,
    buttonTemplate: "web.FormView.Buttons",

    props: (genericProps, view) => {
        const {ArchParser} = view;
        const {arch, relatedModels, resModel} = genericProps;
        const archInfo = new ArchParser().parse(arch, relatedModels, resModel);

        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            buttonTemplate: genericProps.buttonTemplate || view.buttonTemplate,
            Compiler: view.Compiler,
            archInfo,
        };
    },
};

registry.category("views").add("spreadsheet", spreadsheetView);
