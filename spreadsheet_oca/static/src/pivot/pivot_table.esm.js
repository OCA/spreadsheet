/** @odoo-module */
/* Copyright 2024 Tecnativa - Carlos Roca
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */
import {SpreadsheetPivotTable} from "@spreadsheet/pivot/pivot_table";
import {patch} from "@web/core/utils/patch";

patch(SpreadsheetPivotTable.prototype, "spreadsheet_oca.SpreadsheetPivotTable", {
    get _dynamic_cols() {
        return this._cols[this._cols.length - 1] === "dynamic_cols";
    },
    getNumberOfMeasures() {
        if (this._dynamic_cols) {
            // We have disabled the computation of the last column to prevent showing
            // the totalization of the columns when they are of a dynamic type. If
            // shown, it would display the total of all records corresponding to the
            // row, rather than what is being displayed on the screen.
            return 1;
        }
        return this._super(...arguments);
    },
    getColHeaders() {
        if (this._dynamic_cols) {
            // We return a copy of this._cols without the last entry of the array,
            // which indicates that these are dynamic columns.
            var cols = [...this._cols];
            cols.pop();
            return cols;
        }
        return this._super(...arguments);
    },
    getMeasureHeaders() {
        if (this._dynamic_cols) {
            return this._cols[this._cols.length - 2];
        }
        return this._super(...arguments);
    },
    getColWidth() {
        if (this._dynamic_cols) {
            return this._cols[this._cols.length - 2].length;
        }
        return this._super(...arguments);
    },
    getColHeight() {
        if (this._dynamic_cols) {
            return this._cols.length - 1;
        }
        return this._super(...arguments);
    },
    getColMeasureIndex(values) {
        if (this._dynamic_cols) {
            var cols = [...this._cols];
            cols.pop();
            const vals = JSON.stringify(values);
            const maxLength = Math.max(...cols.map((col) => col.length));
            for (let i = 0; i < maxLength; i++) {
                const cellValues = cols.map((col) =>
                    JSON.stringify((col[i] || {}).values)
                );
                if (cellValues.includes(vals)) {
                    return i;
                }
            }
            return -1;
        }
        return this._super(...arguments);
    },
});
