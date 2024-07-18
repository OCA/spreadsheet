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
