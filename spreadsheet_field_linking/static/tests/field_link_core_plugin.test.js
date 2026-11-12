// Side-effect import: registers the plugin and command types.
import "@spreadsheet_field_linking/field_linking/field_link_registration.esm";
import * as spreadsheet from "@odoo/o-spreadsheet";
import {describe, expect, test} from "@odoo/hoot";
import {addRows, setCellContent} from "@spreadsheet/../tests/helpers/commands";
import {collectFieldLinks} from "@spreadsheet_field_linking/field_linking/collect_field_links.esm";
import {createModelWithDataSource} from "@spreadsheet/../tests/helpers/model";
import {defineSpreadsheetModels} from "@spreadsheet/../tests/helpers/data";

const {toCartesian, toZone} = spreadsheet.helpers;

defineSpreadsheetModels();
describe.current.tags("headless");

async function makeModel() {
    const {model} = await createModelWithDataSource({
        modelConfig: {
            custom: {
                linkContext: {
                    isLinkable: true,
                    writable: true,
                    model: "res.partner",
                    resId: 1,
                    recordName: "Partner",
                },
            },
        },
    });
    return model;
}

function mapField(model, xc, chain, selectors) {
    const {col, row} = toCartesian(xc);
    return model.dispatch("MAP_FIELD", {
        sheetId: model.getters.getActiveSheetId(),
        col,
        row,
        chain,
        selectors,
    });
}

function getMapping(model, xc) {
    const {col, row} = toCartesian(xc);
    return model.getters.getFieldMapping({
        sheetId: model.getters.getActiveSheetId(),
        col,
        row,
    });
}

function unmap(model, xc) {
    return model.dispatch("UNMAP_FIELDS", {
        sheetId: model.getters.getActiveSheetId(),
        zone: toZone(xc),
    });
}

describe("field link core plugin", () => {
    test("stores a link on a cell", async () => {
        const model = await makeModel();
        const result = mapField(model, "B2", "line_ids.price", {line_ids: 2});
        expect(result.isSuccessful).toBe(true);
        expect(getMapping(model, "B2")).toEqual({
            chain: "line_ids.price",
            selectors: {line_ids: 2},
        });
    });

    test("clamps a selector position to at least 1", async () => {
        const model = await makeModel();
        mapField(model, "A1", "line_ids.price", {line_ids: 0});
        expect(getMapping(model, "A1").selectors.line_ids).toBe(1);
    });

    test("re-linking a cell to the same target is a no-op", async () => {
        const model = await makeModel();
        mapField(model, "A1", "line_ids.price", {line_ids: 1});
        const result = mapField(model, "A1", "line_ids.price", {line_ids: 1});
        expect(result.isSuccessful).toBe(false);
    });

    test("unmapping clears the links in a zone", async () => {
        const model = await makeModel();
        mapField(model, "A1", "line_ids.price", {line_ids: 1});
        const result = unmap(model, "A1");
        expect(result.isSuccessful).toBe(true);
        expect(getMapping(model, "A1")).toBe(undefined);
    });

    test("unmapping an empty zone is a no-op", async () => {
        const model = await makeModel();
        expect(unmap(model, "A1").isSuccessful).toBe(false);
    });

    test("returns every link", async () => {
        const model = await makeModel();
        mapField(model, "A1", "line_ids.price", {line_ids: 1});
        mapField(model, "B2", "line_ids.qty", {line_ids: 2});
        expect(model.getters.getAllFieldMappings().size).toBe(2);
    });

    test("links survive an export/import round-trip", async () => {
        const model = await makeModel();
        mapField(model, "A1", "line_ids.qty", {line_ids: 3});
        const {model: reloaded} = await createModelWithDataSource({
            spreadsheetData: model.exportData(),
        });
        expect(getMapping(reloaded, "A1")).toEqual({
            chain: "line_ids.qty",
            selectors: {line_ids: 3},
        });
    });

    test("a link follows its cell when rows are inserted above", async () => {
        const model = await makeModel();
        mapField(model, "A3", "line_ids.price", {line_ids: 1});
        addRows(model, "before", 0, 1);
        expect(getMapping(model, "A3")).toBe(undefined);
        expect(getMapping(model, "A4")).toEqual({
            chain: "line_ids.price",
            selectors: {line_ids: 1},
        });
    });

    test("a link is dropped when its row is deleted", async () => {
        const model = await makeModel();
        mapField(model, "A3", "line_ids.price", {line_ids: 1});
        model.dispatch("REMOVE_COLUMNS_ROWS", {
            sheetId: model.getters.getActiveSheetId(),
            dimension: "ROW",
            elements: [2],
        });
        expect(model.getters.getAllFieldMappings().size).toBe(0);
    });

    test("exposes the seeded link context", async () => {
        const model = await makeModel();
        expect(model.getters.getFieldLinkContext().model).toBe("res.partner");
        expect(model.getters.getFieldLinkContext().isLinkable).toBe(true);
    });
});

describe("collect field links", () => {
    test("reads a mapped cell's computed value", async () => {
        const model = await makeModel();
        setCellContent(model, "A1", "42");
        mapField(model, "A1", "note", {});
        const {mappings, errors} = collectFieldLinks(model);
        expect(errors).toEqual([]);
        expect(mappings).toHaveLength(1);
        expect(mappings[0].chain).toBe("note");
        expect(mappings[0].value).toBe(42);
    });

    test("sends null for an empty cell", async () => {
        const model = await makeModel();
        mapField(model, "A1", "note", {});
        expect(collectFieldLinks(model).mappings[0].value).toBe(null);
    });

    test("skips a cell in error", async () => {
        const model = await makeModel();
        setCellContent(model, "A1", "=1/0");
        mapField(model, "A1", "note", {});
        expect(collectFieldLinks(model).mappings).toHaveLength(0);
    });

    test("skips a cell without a chain", async () => {
        const model = await makeModel();
        setCellContent(model, "A1", "42");
        mapField(model, "A1", "", {});
        expect(collectFieldLinks(model).mappings).toHaveLength(0);
    });

    test("flags two cells targeting the same field", async () => {
        const model = await makeModel();
        setCellContent(model, "A1", "1");
        setCellContent(model, "B1", "2");
        mapField(model, "A1", "note", {});
        mapField(model, "B1", "note", {});
        const {mappings, errors} = collectFieldLinks(model);
        expect(mappings).toHaveLength(2);
        expect(errors).toHaveLength(1);
        expect(errors[0]).toInclude("A1");
        expect(errors[0]).toInclude("B1");
    });
});
