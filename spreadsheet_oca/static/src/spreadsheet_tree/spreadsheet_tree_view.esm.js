import {Component, t, useProps} from "@odoo/owl";
import {FileUploader} from "@web/views/fields/file_handler";
import {ListController} from "@web/views/list/list_controller";
import {_t} from "@web/core/l10n/translation";
import {listView} from "@web/views/list/list_view";
import {registry} from "@web/core/registry";
import {standardWidgetProps} from "@web/views/widgets/standard_widget_props";
import {useService} from "@web/core/utils/hooks";

class SpreadsheetFileUploader extends Component {
    static template = "spreadsheet_oca.SpreadsheetFileUploader";
    static components = {FileUploader};
    props = useProps({
        ...standardWidgetProps,
        acceptedFileExtensions: t
            .string()
            .optional(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        record: t.object().optional(),
        togglerTemplate: t.string().optional(),
        slots: t.object().optional(),
        linkText: t.any().optional(_t("Upload a Spreadsheet")),
    });

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.attachmentIdsToProcess = [];
        this.action = useService("action");
    }
    async onFileUploaded(file) {
        const att_data = {
            name: file.name,
            mimetype: file.type,
            raw: file.data,
        };
        const att_id = await this.orm.create("ir.attachment", [att_data], {
            context: this.env.searchModel.context,
        });
        this.attachmentIdsToProcess.push(att_id[0]);
    }
    async onUploadComplete() {
        let action = {};
        try {
            action = await this.orm.call(
                "spreadsheet.spreadsheet",
                "create_document_from_attachment",
                ["", this.attachmentIdsToProcess],
                {context: this.env.searchModel.context}
            );
        } finally {
            // Ensures attachments are cleared on success as well as on error
            this.attachmentIdsToProcess = [];
        }
        if (action.context && action.context.notifications) {
            for (const [file, msg] of Object.entries(action.context.notifications)) {
                this.notification.add(msg, {
                    title: file,
                    type: "info",
                    sticky: true,
                });
            }
            delete action.context.notifications;
        }
        this.action.doAction(action);
    }
}
export class SpreadsheetListController extends ListController {
    static components = {
        ...ListController.components,
        SpreadsheetFileUploader,
    };
}
export const SpreadsheetListView = {
    ...listView,
    Controller: SpreadsheetListController,
    buttonTemplate: "spreadsheet_oca.SpreadsheetTreeView.Buttons",
};

registry.category("views").add("spreadsheet_tree", SpreadsheetListView);
