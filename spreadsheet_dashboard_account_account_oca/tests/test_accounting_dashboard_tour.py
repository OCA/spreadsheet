# Copyright 2022 Tecnativa - Pedro M. Baeza
from odoo.tests.common import tagged

from odoo.addons.spreadsheet.tests.validate_spreadsheet_data import (
    ValidateSpreadsheetData,
)


@tagged("-at_install", "post_install")
class TestSpreadsheetDashboardData(ValidateSpreadsheetData):
    def test_validate_dashboard_data(self):
        dashboard_xml_ids = [
            "spreadsheet_dashboard_account_account_oca.dashboard_accounting",
            "spreadsheet_dashboard_account_account_oca.dashboard_benchmark",
        ]
        for dashboard_xml_id in dashboard_xml_ids:
            dashboard = self.env.ref(dashboard_xml_id)
            with self.subTest(dashboard.name):
                self.validate_spreadsheet_data(dashboard.raw, dashboard.name)
