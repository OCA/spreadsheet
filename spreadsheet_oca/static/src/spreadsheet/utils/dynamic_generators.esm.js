/** @odoo-module **/
/* Copyright 2024 Tecnativa - Carlos Roca
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

/**
 * Calculates the rows to calculate the dynamic values. This can be used to make
 * a top of data.
 *
 * When the rows has just a indentation of 1, the number of rows will be the
 * final result.
 *
 * Example:
 * number_of_rows = 2
 * max_indentation = 1
 * - first element
 * - second element
 *
 * The pivot allows to increase the indentation, when it happens, the number of
 * rows will be propagated to each indentation.
 *
 * Example:
 * number_of_rows = 2
 * max_indentation = 2
 * - first element
 *     - first subelement
 *     - second subelement
 * - second element
 *     - first subelement
 *     - second subelement
 *
 * @param {Array} fields
 * @param {Number} number_of_rows
 * @param {Number} indent
 * @param {Number} max_indentation
 * @param {Array} parent_indexes
 * @returns {Array}
 */
export function makeDynamicRows(
    fields,
    number_of_rows,
    indent,
    max_indentation,
    parent_indexes = []
) {
    var rows = [];
    for (var index = 1; index <= number_of_rows; index++) {
        rows.push({
            fields: fields.slice(0, indent).map((f) => "#" + f),
            indent,
            values: [...parent_indexes, index],
        });
        if (indent < max_indentation) {
            rows = rows.concat(
                makeDynamicRows(fields, number_of_rows, indent + 1, max_indentation, [
                    ...parent_indexes,
                    index,
                ])
            );
        }
    }
    return rows;
}

function _incrementArray(arr, base) {
    let carry = 1;
    for (let i = arr.length - 1; i >= 0; i--) {
        const sum = arr[i] + carry;
        arr[i] = sum % base ? sum % base : 1;
        carry = Math.floor(sum / base);
        if (carry === 0) break;
    }

    return arr;
}

function _getColLevelInfo(fields, number_of_cols, width) {
    const col_info = [];
    var values = Array.from({length: fields.length}, () => 1);
    for (var f = Math.pow(number_of_cols, fields.length - 1) - 1; f >= 0; f--) {
        for (var c = 1; c <= number_of_cols; c++) {
            col_info.push({
                fields,
                values,
                width,
            });
            values = _incrementArray([...values], number_of_cols + 1);
        }
    }
    return col_info;
}

/**
 *
 * @param {Array} fields
 * @param {Number} number_of_cols
 * @param {Number} indent
 * @param {Number} max_indentation
 * @param {Array} parent_indexes
 * @returns {Array}
 */
export function makeDynamicCols(fields, number_of_cols, measures) {
    var cols = [];
    const max_width =
        (Math.pow(number_of_cols, fields.length) * measures.length) / number_of_cols;
    for (var index = 0; index < fields.length; index++) {
        const width = max_width / Math.pow(number_of_cols, index);
        const newFields = fields.slice(0, index + 1).map((f) => "#" + f);
        cols.push(_getColLevelInfo(newFields, number_of_cols, width));
    }
    const measuresCols = [];
    const lastCols = cols[cols.length - 1];
    for (var col of lastCols) {
        for (var measure of measures) {
            measuresCols.push({
                fields: [...col.fields, "measure"],
                values: [...col.values, measure],
                width: 1,
            });
        }
    }
    cols.push(measuresCols);
    cols.push("dynamic_cols");
    return cols;
}
