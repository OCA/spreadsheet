import {registry} from "@web/core/registry";

const openSpreadsheetSteps = [
    {
        trigger: ".o_kanban_record:contains(Tour spreadsheet)",
        content: "The spreadsheet is displayed in the kanban view",
    },
    {
        trigger: ".o_switch_view.o_list",
        content: "Switch to the list view",
        run: "click",
    },
    {
        trigger: ".o_list_view .o_button_upload_spreadsheet",
        content: "The upload button is displayed",
    },
    {
        trigger: ".o_data_row td[name='name']:contains(Tour spreadsheet)",
        content: "Open the spreadsheet record",
        run: "click",
    },
    {
        trigger: ".o_form_view button[name='open_spreadsheet']",
        content: "Open the spreadsheet",
        run: "click",
    },
    {
        trigger: ".o_spreadsheet_oca_container .o-spreadsheet .o-grid",
        content: "The spreadsheet is loaded",
    },
];

const insertFromViewSteps = (viewType, buttonSelectors) => [
    // The action opens in list view, and switching to the active view reloads
    // it, closing the import wizard if it was opened in the meantime
    ...(viewType === "list"
        ? []
        : [
              {
                  trigger: `.o_switch_view.o_${viewType}`,
                  content: `Switch to the ${viewType} view`,
                  run: "click",
              },
          ]),
    ...[buttonSelectors].flat().map((trigger) => ({
        trigger,
        content: "Add to spreadsheet",
        run: "click",
    })),
    {
        trigger: ".modal div[name='name'] input",
        content: "Name of the new spreadsheet",
        run: `edit Tour ${viewType} spreadsheet`,
    },
    {
        trigger: ".modal button[name='insert_pivot']",
        content: "Insert in a new spreadsheet",
        run: "click",
    },
    {
        trigger: ".o_spreadsheet_oca_container .o-spreadsheet .o-grid",
        content: "The spreadsheet is loaded",
    },
    {
        trigger: ".o_spreadsheet_oca_name",
        content: "The spreadsheet name is displayed",
    },
];

registry.category("web_tour.tours").add("spreadsheet_oca_edit", {
    steps: () => [
        ...openSpreadsheetSteps,
        {
            trigger: ".o-topbar-composer .o-composer",
            content: "Focus the composer",
            run: "click",
        },
        {
            trigger: ".o-topbar-composer .o-composer",
            content: "Write a formula",
            run() {
                // The composer is a "plaintext-only" contenteditable
                this.anchor.textContent = "=1+41";
                this.anchor.dispatchEvent(new InputEvent("input", {bubbles: true}));
            },
        },
        {
            trigger: ".o-topbar-composer .o-composer",
            content: "Validate",
            run: "press Enter",
        },
        {
            trigger: ".o-topbar-menu[data-id='file']",
            content: "Open the File menu",
            run: "click",
        },
        {
            trigger: ".o-menu-item[data-name='save']",
            content: "Save the spreadsheet",
            run: "click",
        },
        {
            trigger: ".o_spreadsheet_oca_name",
            content: "The spreadsheet is still displayed",
        },
    ],
});

const openTopbarMenu = (menu, ...items) => [
    {
        trigger: `.o-topbar-menu[data-id='${menu}']`,
        content: `Open the ${menu} menu`,
        run: "click",
    },
    ...items.map((item) => ({
        trigger: `.o-menu-item[data-name='${item}']`,
        content: `Click on ${item}`,
        run: "click",
    })),
];

registry.category("web_tour.tours").add("spreadsheet_oca_insert_pivot", {
    steps: () => [
        ...insertFromViewSteps("pivot", ".o_pivot_add_spreadsheet"),
        ...openTopbarMenu("data", "pivot_data_sources", "item_pivot_1"),
        {
            trigger: ".o-sidePanel .o_spreadsheet_oca_pivot_panel_info",
            content: "The pivot side panel is displayed",
        },
        ...openTopbarMenu("file", "filters"),
        {
            trigger: ".o-sidePanel .o-sidePanelButtons button:contains(Add date)",
            content: "Add a date filter",
            run: "click",
        },
        {
            trigger: ".o-sidePanel .o_spreadsheet_oca_filter_label_input",
            content: "Filter label",
            run: "edit Tour date filter",
        },
        {
            trigger: ".o-sidePanel .o_spreadsheet_oca_filter_save",
            content: "Save the filter",
            run: "click",
        },
        {
            trigger:
                ".o-sidePanel .spreadsheet_oca_filter_label:contains(Tour date filter)",
            content: "The filter is displayed in the filter panel",
        },
    ],
});

registry.category("web_tour.tours").add("spreadsheet_oca_insert_graph", {
    steps: () => [
        ...insertFromViewSteps("graph", ".o_graph_add_spreadsheet"),
        {
            trigger: ".o-figure .o-chart-container",
            content: "Edit the chart",
            run: "dblclick",
        },
        {
            trigger: ".o-sidePanel .o_spreadsheet_oca_chart_datasource",
            content: "The Odoo data source of the chart is displayed",
        },
        {
            trigger: ".o-sidePanel .o_spreadsheet_oca_odoo_menu",
            content: "The Odoo menu link is displayed",
        },
    ],
});

registry.category("web_tour.tours").add("spreadsheet_oca_insert_list", {
    steps: () => [
        ...insertFromViewSteps("list", [
            ".o_cp_action_menus .dropdown-toggle",
            ".o_spreadsheet_oca_insert_list",
        ]),
        ...openTopbarMenu("data", "data_source_list_1"),
        {
            trigger: ".o-sidePanel .o_spreadsheet_oca_datasource_panel",
            content: "The list side panel is displayed",
        },
    ],
});

registry.category("web_tour.tours").add("spreadsheet_oca_reopen", {
    steps: () => [
        {
            trigger: ".o_form_view button[name='open_spreadsheet']",
            content: "Open the spreadsheet",
            run: "click",
        },
        {
            trigger: ".o_spreadsheet_oca_container .o-spreadsheet .o-grid",
            content: "The spreadsheet is loaded",
        },
        ...openTopbarMenu("file", "filters"),
        {
            trigger:
                ".o-sidePanel .spreadsheet_oca_filter_label:contains(Tour date filter)",
            content: "The filter added in the previous session is there",
        },
        ...openTopbarMenu("data", "pivot_data_sources", "item_pivot_1"),
        {
            trigger: ".o-sidePanel .o_spreadsheet_oca_pivot_panel_info",
            content: "The pivot added in the previous session is there",
        },
    ],
});
