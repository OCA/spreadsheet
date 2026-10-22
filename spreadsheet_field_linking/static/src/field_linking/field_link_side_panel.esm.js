import {Component, onWillStart, useState} from "@odoo/owl";
import {components, helpers} from "@odoo/o-spreadsheet";
import {ModelFieldSelector} from "@web/core/model_field_selector/model_field_selector";
import {useService} from "@web/core/utils/hooks";

const {Section} = components;
const {positionToZone} = helpers;

export class FieldLinkSidePanel extends Component {
    static template = "spreadsheet_field_linking.FieldLinkPanel";
    static components = {ModelFieldSelector, Section};
    static props = {
        onCloseSidePanel: Function,
        position: Object,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({saved: false, selectors: []});
        onWillStart(async () => {
            this.state.selectors = await this._fetchSelectors(this.fieldMapping.chain);
        });
    }

    get context() {
        return this.env.model.getters.getFieldLinkContext();
    }

    get fieldMapping() {
        return this.env.model.getters.getFieldMapping(this.props.position);
    }

    get cellReference() {
        const {sheetId} = this.props.position;
        const range = this.env.model.getters.getRangeFromZone(
            sheetId,
            positionToZone(this.props.position)
        );
        return this.env.model.getters.getRangeString(range, sheetId);
    }

    filterField(field) {
        return field.store && !field.readonly;
    }

    lineLabel(segment) {
        const entry = this.state.selectors.find((sel) => sel.segment === segment);
        const position = this.fieldMapping.selectors[segment];
        return entry?.labels.find((line) => line.position === position)?.label || "";
    }

    async _fetchSelectors(chain) {
        if (!chain) {
            return [];
        }
        return this.orm.call("spreadsheet.spreadsheet", "get_link_selectors", [
            [this.context.spreadsheetId],
            chain,
        ]);
    }

    async updateChain(chain) {
        const selectors = await this._fetchSelectors(chain);
        const values = {};
        selectors.forEach((entry, index) => {
            // Default the leading hop to the cell's own row, deeper hops to 1.
            values[entry.segment] =
                this.fieldMapping.selectors[entry.segment] ||
                (index === 0 ? this.props.position.row + 1 : 1);
        });
        this.state.selectors = selectors;
        this._update({chain, selectors: values});
    }

    updatePosition(segment, ev) {
        const position = parseInt(ev.target.value, 10);
        if (position >= 1) {
            this._update({
                selectors: {...this.fieldMapping.selectors, [segment]: position},
            });
        }
    }

    _update(partial) {
        const {sheetId, col, row} = this.props.position;
        const result = this.env.model.dispatch("MAP_FIELD", {
            sheetId,
            col,
            row,
            chain: this.fieldMapping.chain,
            selectors: this.fieldMapping.selectors,
            ...partial,
        });
        if (result.isSuccessful) {
            this.state.saved = true;
            setTimeout(() => (this.state.saved = false), 1500);
        }
    }
}
