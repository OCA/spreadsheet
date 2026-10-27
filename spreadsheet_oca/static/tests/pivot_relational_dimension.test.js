import {Component, xml} from "@odoo/owl";
import {contains, mountWithCleanup} from "@web/../tests/web_test_helpers";
import {describe, expect, test} from "@odoo/hoot";
import {Spreadsheet} from "@odoo/o-spreadsheet";
import {animationFrame} from "@odoo/hoot-mock";
import {createSpreadsheetWithPivot} from "@spreadsheet/../tests/helpers/pivot";
import {defineSpreadsheetModels} from "@spreadsheet/../tests/helpers/data";
import {waitForDataLoaded} from "@spreadsheet/helpers/model";

describe.current.tags("desktop");
defineSpreadsheetModels();

class Parent extends Component {
    static template = xml`<Spreadsheet model="props.model"/>`;
    static components = {Spreadsheet};
    static props = {model: Object};
}

const ITEM = ".o_model_field_selector_popover_item";

async function openPivotPanel() {
    const {model, env, pivotId} = await createSpreadsheetWithPivot();
    await mountWithCleanup(Parent, {
        env,
        props: {model},
        noMainContainer: true,
    });
    await animationFrame();
    await contains(".o-topbar-menu[data-id='data']").click();
    await contains(".o-menu-item[data-name='item_pivot_1']").click();
    return {model, pivotId};
}

async function addTemplateColumn() {
    await contains(".o-spreadsheet .add-dimension").click();
    await contains(
        `${ITEM}[data-name='product_id'] .o_model_field_selector_popover_relation_icon`
    ).click();
    await contains(
        `${ITEM}[data-name='template_id'] .o_model_field_selector_popover_item_name`
    ).click();
}

function getColumnFieldNames(model, pivotId) {
    return model.getters
        .getPivotCoreDefinition(pivotId)
        .columns.map((col) => col.fieldName);
}

test("pivot 'Add' only allows following many2one relations", async () => {
    await openPivotPanel();
    await contains(".o-spreadsheet .add-dimension").click();
    expect(
        `${ITEM}[data-name='product_id'] .o_model_field_selector_popover_relation_icon`
    ).toHaveCount(1);
    expect(`${ITEM}[data-name='tag_ids']`).toHaveCount(1);
    expect(
        `${ITEM}[data-name='tag_ids'] .o_model_field_selector_popover_relation_icon`
    ).toHaveCount(0);
});

test("can add a related field as pivot column", async () => {
    const {model, pivotId} = await openPivotPanel();
    await addTemplateColumn();
    expect(getColumnFieldNames(model, pivotId)).toEqual([
        "foo",
        "product_id.template_id",
    ]);
    await waitForDataLoaded(model);
    await animationFrame();
    expect(
        ".o-spreadsheet .pivot-dimension:contains('Product > Template')"
    ).toHaveCount(1);
});

test("an already used dimension is not added twice", async () => {
    const {model, pivotId} = await openPivotPanel();
    await addTemplateColumn();
    await addTemplateColumn();
    expect(getColumnFieldNames(model, pivotId)).toEqual([
        "foo",
        "product_id.template_id",
    ]);
});
