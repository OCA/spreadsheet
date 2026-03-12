/** @odoo-module */

import {registry} from "@web/core/registry";

registry.category("web_tour.tours").add("spreadsheet_oca_features", {
    url: "/odoo",
    steps: () => [
        // 1. Click the Spreadsheets menu
        {
            trigger:
                ".o_menu_sections a:contains('Spreadsheets'), .o_navbar a:contains('Spreadsheets'), a.dropdown-item:contains('Spreadsheets')",
            content: "Open the Spreadsheets menu to see your dashboards.",
            run: "click",
        },
        // 2. Welcome on kanban view
        {
            trigger: ".o_kanban_view",
            content:
                "Welcome to Spreadsheets! You're looking at your spreadsheet dashboards.",
            run() {
                // Observation step — no interaction
            },
        },
        // 2. Click the Sales Pipeline Summary card
        {
            trigger: ".o_kanban_record:contains('Sales Pipeline Summary')",
            content:
                "Open the Sales Pipeline Summary spreadsheet to explore its features.",
            run: "click",
        },
        // 3. On form view — point out smart buttons row
        {
            trigger: ".o_form_view div[name='button_box'], .o_form_view #button_box",
            content:
                "These smart buttons give you quick access to all features: alerts, scenarios, parameters, and more.",
            run() {
                // Observation step — no interaction
            },
        },
        // 4. Click KPI Alerts smart button
        {
            trigger:
                "button[name='action_open_alerts'], div[name='alert_count'] .oe_stat_button",
            content: "Click to view KPI Alerts configured for this spreadsheet.",
            run: "click",
        },
        // 5. Show the alert list
        {
            trigger: ".o_list_view, .o_kanban_view",
            content:
                "KPI Alerts monitor cell values and notify you when thresholds are crossed. You can set edge triggers (notify once) or level triggers (notify every cycle).",
            run() {
                // Observation step — no interaction
            },
        },
        // 6. Go back via breadcrumb
        {
            trigger: ".o_back_button, .breadcrumb-item a",
            content: "Go back to the spreadsheet form.",
            run: "click",
        },
        // 7. Click Scenarios smart button
        {
            trigger:
                "button[name='action_open_scenarios'], div[name='scenario_count'] .oe_stat_button",
            content: "Click to view What-If Scenarios.",
            run: "click",
        },
        // 8. Show scenarios list
        {
            trigger: ".o_list_view, .o_kanban_view",
            content:
                "What-If Scenarios let you model different outcomes without duplicating your spreadsheet. Try the Optimistic or Pessimistic variants.",
            run() {
                // Observation step — no interaction
            },
        },
        // 9. Go back via breadcrumb
        {
            trigger: ".o_back_button, .breadcrumb-item a",
            content: "Go back to the spreadsheet form.",
            run: "click",
        },
        // 10. Click Input Parameters smart button
        {
            trigger:
                "button[name='action_open_input_params'], div[name='input_param_count'] .oe_stat_button",
            content: "Click to view Input Parameters.",
            run: "click",
        },
        // 11. Show parameters list
        {
            trigger: ".o_list_view, .o_kanban_view",
            content:
                "Input Parameters bind named cells to server-side domain substitution for scheduled refreshes. Change a date here and the next refresh picks it up automatically.",
            run() {
                // Observation step — no interaction
            },
        },
        // 12. Go back via breadcrumb
        {
            trigger: ".o_back_button, .breadcrumb-item a",
            content: "Go back to the spreadsheet form.",
            run: "click",
        },
        // 13. Point to Export XLSX button
        {
            trigger: "button[name='action_export_xlsx']",
            content:
                "Export XLSX generates a server-side .xlsx file with fresh pivot data — no browser extension needed.",
            run() {
                // Observation step — no interaction
            },
        },
        // 14. Point to Refresh Schedules smart button
        {
            trigger:
                "button[name='action_open_refresh_schedules'], div[name='refresh_schedule_count'] .oe_stat_button",
            content:
                "Set up automated data refresh on a schedule. The cron fetches fresh pivot data and emails a summary to subscribed partners.",
            run() {
                // Observation step — no interaction
            },
        },
        // 15. Final step
        {
            trigger: ".o_form_view",
            content:
                "You're all set! Explore each feature to unlock the full power of your spreadsheets.",
            run() {
                // Observation step — no interaction
            },
        },
    ],
});
