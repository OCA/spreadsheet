import {Component, onWillUnmount, xml} from "@odoo/owl";
import {contains, mountWithCleanup} from "@web/../tests/web_test_helpers";
import {describe, expect, test} from "@odoo/hoot";
import {getCellFormula, getCellValue} from "@spreadsheet/../tests/helpers/getters";
import {ListPanel} from "@spreadsheet_oca/spreadsheet/bundle/filter_panel_datasources.esm";
import {animationFrame} from "@odoo/hoot-mock";
import {createSpreadsheetWithList} from "@spreadsheet/../tests/helpers/list";
import {defineSpreadsheetModels} from "@spreadsheet/../tests/helpers/data";
import {waitForDataLoaded} from "@spreadsheet/helpers/model";

describe.current.tags("desktop");
defineSpreadsheetModels();

/**
 * O-spreadsheet re-renders its side panels on every model update; do the same
 * here since the panel is mounted outside of the spreadsheet component.
 */
class Parent extends Component {
    static template = xml`<ListPanel listId="props.listId"/>`;
    static components = {ListPanel};
    static props = {listId: String};
    setup() {
        const model = this.env.model;
        model.on("update", this, () => this.render(true));
        onWillUnmount(() => model.off("update", this));
    }
}

async function mountListPanel(columns = ["foo", "product_id"]) {
    const {model, env} = await createSpreadsheetWithList({columns, linesNumber: 2});
    const listId = model.getters.getListIds()[0];
    await mountWithCleanup(Parent, {
        env,
        componentEnv: {
            model,
            openSidePanel: () => true,
            askConfirmation: (message, callback) => callback(),
        },
        props: {listId},
    });
    return {model, listId};
}

function getColumns(model, listId) {
    return model.getters.getListDefinition(listId).columns;
}

async function addColumnFromSelector(fieldName, subFieldName) {
    await contains(
        ".o_spreadsheet_oca_list_column_selector .o_model_field_selector"
    ).click();
    await contains(
        `.o_model_field_selector_popover_item[data-name='${fieldName}'] .o_model_field_selector_popover_relation_icon`
    ).click();
    await contains(
        `.o_model_field_selector_popover_item[data-name='${subFieldName}'] .o_model_field_selector_popover_item_name`
    ).click();
    await contains(".o_spreadsheet_oca_list_column_add").click();
}

test("shows the current columns with their labels", async () => {
    await mountListPanel();
    expect(".o_spreadsheet_oca_list_column span").toHaveCount(2);
    expect(".o_spreadsheet_oca_list_column span:first").toHaveText("Foo");
    expect(".o_spreadsheet_oca_list_column span:last").toHaveText("Product");
});

test("can add a related field as a column", async () => {
    const {model, listId} = await mountListPanel();
    await addColumnFromSelector("product_id", "name");
    expect(getColumns(model, listId)).toEqual(["foo", "product_id", "product_id.name"]);
    await animationFrame();
    expect(".o_spreadsheet_oca_list_column span:last").toHaveText(
        "Product > Product Name"
    );
});

test("does not add the same column twice", async () => {
    const {model, listId} = await mountListPanel(["foo"]);
    await addColumnFromSelector("product_id", "name");
    await addColumnFromSelector("product_id", "name");
    expect(getColumns(model, listId)).toEqual(["foo", "product_id.name"]);
});

test("can remove and reorder columns", async () => {
    const {model, listId} = await mountListPanel(["foo", "bar", "product_id"]);
    await contains(
        ".o_spreadsheet_oca_list_column:last .o_spreadsheet_oca_list_column_up"
    ).click();
    expect(getColumns(model, listId)).toEqual(["foo", "product_id", "bar"]);
    await contains(
        ".o_spreadsheet_oca_list_column:first .o_spreadsheet_oca_list_column_remove"
    ).click();
    expect(getColumns(model, listId)).toEqual(["product_id", "bar"]);
});

test("re-inserting the list writes the related column", async () => {
    const {model} = await mountListPanel(["foo"]);
    await addColumnFromSelector("product_id", "name");
    await contains(".o-sidePanelButtons .btn-success").click();
    expect(getCellFormula(model, "B1")).toBe(
        '=ODOO.LIST.HEADER(1,"product_id.name","Product > Product Name")'
    );
    expect(getCellFormula(model, "B2")).toBe('=ODOO.LIST(1,1,"product_id.name")');
    await waitForDataLoaded(model);
    expect(getCellValue(model, "B1")).toBe("Product > Product Name");
    expect(getCellValue(model, "B2")).toBe("xphone");
});
