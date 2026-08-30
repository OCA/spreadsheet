import {
    contains,
    makeDialogMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import {describe, expect, test} from "@odoo/hoot";

import {ShareManageDialog} from "@spreadsheet_dashboard_oca/bundle/share_manage/share_manage_dialog";

describe.current.tags("desktop");

const SHARES = [
    {
        id: 1,
        full_url: "http://localhost/dashboard/share/1/token1",
        create_date: "2026-08-04T10:00:00",
        create_uid: "Raoul",
        name: "DeepSeek API Giderleri",
    },
    {
        id: 2,
        full_url: "http://localhost/dashboard/share/2/token2",
        create_date: "2026-08-04T11:00:00",
        create_uid: "Bob",
        name: "DeepSeek API Giderleri",
    },
];

async function mountDialog(env, {shares = SHARES} = {}) {
    patchWithCleanup(env.services.orm, {
        async call(model, method) {
            if (method === "action_get_dashboard_shares") {
                return shares;
            }
            if (method === "action_unshare") {
                return true;
            }
            throw new Error(`Unexpected method: ${method}`);
        },
    });
    await mountWithCleanup(ShareManageDialog, {
        env,
        props: {
            dashboardId: 3,
            title: "DeepSeek API Giderleri - Manage shares",
        },
    });
}

test("renders the share list", async () => {
    const env = await makeDialogMockEnv();
    await mountDialog(env);
    expect(".modal-header").toHaveText(/Manage shares/);
    expect("tbody tr").toHaveCount(2);
    expect("tbody tr").toHaveText(/Raoul/);
    expect("tbody tr").toHaveText(/Bob/);
    expect("tbody tr").toHaveText(/dashboard\/share\/1\/token1/);
});

test("shows empty state when there are no shares", async () => {
    const env = await makeDialogMockEnv();
    await mountDialog(env, {shares: []});
    expect("tbody").toHaveCount(0);
    expect("body").toHaveText(/No shares yet/);
});

test("revoke removes the row and notifies the badge", async () => {
    const env = await makeDialogMockEnv();
    let busEvents = 0;
    env.bus.addEventListener("dashboards-shares-updated", () => busEvents++);
    await mountDialog(env);
    expect("tbody tr").toHaveCount(2);
    await contains(".btn-danger").click();
    expect("tbody tr").toHaveCount(1);
    expect("tbody tr").toHaveText(/Bob/);
    expect("tbody tr").toHaveText(/dashboard\/share\/2\/token2/);
    expect(busEvents).toBe(1);
});
