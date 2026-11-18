# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import datetime
from unittest import mock

from odoo import Command
from odoo.tests.common import TransactionCase

from odoo.addons.mis_builder.models.mis_report import MisReport


class TestSpreadsheetMisBuilder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Spreadsheet MIS"})
        cls.env.user.company_ids = [Command.link(cls.company.id)]
        cls.account_ar = cls.env["account.account"].create(
            {
                "company_ids": cls.company.ids,
                "code": "400AR",
                "name": "Receivable",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        cls.account_in = cls.env["account.account"].create(
            {
                "company_ids": cls.company.ids,
                "code": "700IN",
                "name": "Income",
                "account_type": "income",
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "company_id": cls.company.id,
                "name": "Sale journal",
                "code": "VEN",
                "type": "sale",
            }
        )
        cls._create_move(datetime.date(2026, 1, 15), 100)
        cls._create_move(datetime.date(2026, 2, 15), 300)
        cls._create_move(datetime.date(2026, 2, 20), 50, post=False)
        cls.style = cls.env["mis.report.style"].create(
            {
                "name": "Spreadsheet MIS bold",
                "font_weight_inherit": False,
                "font_weight": "bold",
                "dp_inherit": False,
                "dp": 2,
            }
        )
        cls.report = cls.env["mis.report"].create(
            {
                "name": "Spreadsheet MIS report",
                "kpi_ids": [
                    Command.create(
                        {
                            "name": "income",
                            "description": "Income",
                            "expression": "-balp[700IN]",
                            "style_id": cls.style.id,
                            "sequence": 1,
                        }
                    ),
                    Command.create(
                        {
                            "name": "receivable",
                            "description": "Receivable",
                            "expression": "bale[400AR]",
                            "compare_method": "diff",
                            "sequence": 2,
                        }
                    ),
                    Command.create(
                        {
                            "name": "margin",
                            "description": "Margin",
                            "expression": "income / receivable",
                            "type": "pct",
                            "sequence": 3,
                        }
                    ),
                ],
            }
        )

    @classmethod
    def _create_move(cls, date, amount, post=True):
        move = cls.env["account.move"].create(
            {
                "date": date,
                "journal_id": cls.journal.id,
                "line_ids": [
                    Command.create(
                        {"account_id": cls.account_ar.id, "debit": amount},
                    ),
                    Command.create(
                        {"account_id": cls.account_in.id, "credit": amount},
                    ),
                ],
            }
        )
        if post:
            move.action_post()
        return move

    def _args(self, kpi, date_from, date_to, **kwargs):
        return dict(
            report_id=self.report.id,
            kpi=kpi,
            date_from=date_from,
            date_to=date_to,
            company_ids=self.company.ids,
            **kwargs,
        )

    def _fetch(self, *args_list):
        return self.env["mis.report"].spreadsheet_fetch_kpi(list(args_list))

    def test_fetch_kpi(self):
        january, february, quarter, receivable, margin = self._fetch(
            self._args("income", "2026-01-01", "2026-01-31"),
            self._args("income", "2026-02-01", "2026-02-28"),
            self._args("income", "2026-01-01", "2026-03-31"),
            self._args("receivable", "2026-01-01", "2026-03-31"),
            self._args("margin", "2026-01-01", "2026-03-31"),
        )
        self.assertEqual(january, {"value": 100, "format": "#,##0.00"})
        self.assertEqual(february["value"], 300)
        self.assertEqual(quarter["value"], 400)
        self.assertEqual(receivable, {"value": 400, "format": "#,##0"})
        self.assertEqual(margin, {"value": 1, "format": "0%"})

    def test_fetch_kpi_unposted(self):
        posted, with_draft = self._fetch(
            self._args("income", "2026-02-01", "2026-02-28"),
            self._args("income", "2026-02-01", "2026-02-28", include_unposted=True),
        )
        self.assertEqual(posted["value"], 300)
        self.assertEqual(with_draft["value"], 350)

    def test_fetch_kpi_no_data(self):
        (result,) = self._fetch(self._args("income", "2025-01-01", "2025-01-31"))
        self.assertIs(result["value"], False)

    def test_fetch_kpi_one_evaluation_per_period(self):
        with mock.patch.object(
            MisReport, "evaluate", autospec=True, side_effect=MisReport.evaluate
        ) as evaluate:
            self._fetch(
                self._args("income", "2026-01-01", "2026-01-31"),
                self._args("receivable", "2026-01-01", "2026-01-31"),
                self._args("margin", "2026-01-01", "2026-01-31"),
                self._args("income", "2026-02-01", "2026-02-28"),
            )
        self.assertEqual(evaluate.call_count, 2)

    def test_fetch_kpi_errors(self):
        unknown_kpi, unknown_report, bad_dates, bad_company, ok = self._fetch(
            self._args("unknown", "2026-01-01", "2026-01-31"),
            dict(self._args("income", "2026-01-01", "2026-01-31"), report_id=0),
            self._args("income", "2026-02-01", "2026-01-31"),
            dict(self._args("income", "2026-01-01", "2026-01-31"), company_ids=[0]),
            self._args("income", "2026-01-01", "2026-01-31"),
        )
        self.assertIn("unknown", unknown_kpi["error"])
        self.assertIn("not found", unknown_report["error"])
        self.assertIn("start date", bad_dates["error"])
        self.assertIn("companies", bad_company["error"])
        self.assertEqual(ok["value"], 100)

    def test_fetch_kpi_subkpi(self):
        report = self.env["mis.report"].create(
            {
                "name": "Spreadsheet MIS sub-KPI report",
                "subkpi_ids": [
                    Command.create({"name": "sk1", "description": "One"}),
                    Command.create({"name": "sk2", "description": "Two"}),
                ],
            }
        )
        self.env["mis.report.kpi"].create(
            {
                "report_id": report.id,
                "name": "multi",
                "description": "Multi",
                "multi": True,
                "expression_ids": [
                    Command.create(
                        {"name": "-balp[700IN]", "subkpi_id": report.subkpi_ids[0].id}
                    ),
                    Command.create(
                        {"name": "bale[400AR]", "subkpi_id": report.subkpi_ids[1].id}
                    ),
                ],
            }
        )
        args = dict(
            self._args("multi", "2026-01-01", "2026-01-31"), report_id=report.id
        )
        missing, first, second, unknown = self._fetch(
            args,
            dict(args, subkpi="sk1"),
            dict(args, subkpi="sk2"),
            dict(args, subkpi="sk3"),
        )
        self.assertIn("sub-KPIs", missing["error"])
        self.assertEqual(first["value"], 100)
        self.assertEqual(second["value"], 100)
        self.assertIn("sk3", unknown["error"])

    def _create_instance(self):
        instance = self.env["mis.report.instance"].create(
            {
                "name": "Spreadsheet MIS instance",
                "report_id": self.report.id,
                "company_id": self.company.id,
                "comparison_mode": True,
                "date": "2026-02-10",
                "period_ids": [
                    Command.create(
                        {
                            "name": "previous",
                            "mode": "relative",
                            "type": "m",
                            "offset": -1,
                            "duration": 1,
                            "sequence": 1,
                        }
                    ),
                    Command.create(
                        {
                            "name": "current",
                            "mode": "relative",
                            "type": "m",
                            "offset": 0,
                            "duration": 1,
                            "sequence": 2,
                        }
                    ),
                    Command.create(
                        {
                            "name": "fixed",
                            "mode": "fix",
                            "manual_date_from": "2026-01-01",
                            "manual_date_to": "2026-03-31",
                            "sequence": 3,
                        }
                    ),
                ],
            }
        )
        previous, current, _fixed = instance.period_ids
        instance.period_ids = [
            Command.create(
                {
                    "name": "sum",
                    "mode": "none",
                    "source": "sumcol",
                    "source_sumcol_ids": [
                        Command.create({"period_to_sum_id": previous.id, "sign": "+"}),
                        Command.create({"period_to_sum_id": current.id, "sign": "-"}),
                    ],
                    "sequence": 4,
                }
            ),
            Command.create(
                {
                    "name": "compare",
                    "mode": "none",
                    "source": "cmpcol",
                    "source_cmpcol_from_id": previous.id,
                    "source_cmpcol_to_id": current.id,
                    "sequence": 5,
                }
            ),
        ]
        return instance

    def test_export_spreadsheet(self):
        instance = self._create_instance()
        action = instance.action_export_spreadsheet()
        self.assertEqual(action["tag"], "action_spreadsheet_oca")
        spreadsheet = self.env["spreadsheet.spreadsheet"].browse(
            action["params"]["spreadsheet_id"]
        )
        self.assertEqual(spreadsheet.name, instance.name)
        data = spreadsheet.spreadsheet_raw
        sheet = data["sheets"][0]
        cells = {xc: cell["content"] for xc, cell in sheet["cells"].items()}
        # parameters
        self.assertEqual(cells["B2"], str(self.report.id))
        self.assertEqual(cells["B3"], f'="{self.company.id}"')
        self.assertEqual(cells["B4"], "FALSE")
        self.assertEqual(cells["B5"], "=DATE(2026,2,10)")
        # relative periods follow the base date, fixed ones do not
        self.assertEqual(cells["B7"], "=EDATE(EOMONTH($B$5,-1)+1,-1)")
        self.assertEqual(cells["B8"], "=EOMONTH($B$5,-1)")
        self.assertEqual(cells["C7"], "=EDATE(EOMONTH($B$5,-1)+1,0)")
        self.assertEqual(cells["C8"], "=EOMONTH($B$5,0)")
        self.assertEqual(cells["D7"], "=DATE(2026,1,1)")
        self.assertEqual(cells["D8"], "=DATE(2026,3,31)")
        self.assertEqual(
            [cells[xc] for xc in ("B9", "C9", "D9", "E9", "F9")],
            ["previous", "current", "fixed", "sum", "compare"],
        )
        # KPI rows
        self.assertEqual(cells["A10"], "Income")
        self.assertEqual(cells["B10"], '=MIS.KPI($B$2,"income",B$7,B$8,$B$3,$B$4)')
        self.assertEqual(cells["D11"], '=MIS.KPI($B$2,"receivable",D$7,D$8,$B$3,$B$4)')
        # sum and comparison columns are plain cell formulas
        self.assertEqual(cells["E10"], "=+B10-C10")
        self.assertEqual(cells["F10"], '=IF(B10=0,"",(C10-B10)/ABS(B10))')
        self.assertEqual(cells["F11"], "=C11-B11")
        self.assertEqual(cells["F12"], "=(C12-B12)*100")
        # styles and formats
        styles = data["styles"]
        formats = data["formats"]
        self.assertTrue(styles[str(sheet["styles"]["A10"])]["bold"])
        self.assertEqual(formats[str(sheet["formats"]["B10"])], "#,##0.00")
        self.assertEqual(formats[str(sheet["formats"]["B12"])], "0%")
        self.assertEqual(formats[str(sheet["formats"]["F10"])], "0.0%")

    def test_export_spreadsheet_static_column(self):
        instance = self._create_instance()
        instance.period_ids[0].analytic_domain = "[('partner_id', '=', False)]"
        data = instance._spreadsheet_data()
        sheet = data["sheets"][0]
        cells = {xc: cell["content"] for xc, cell in sheet["cells"].items()}
        self.assertEqual(cells["B9"], "previous (static)")
        self.assertNotIn("B7", cells)
        self.assertEqual(cells["B10"], "100.0")
        self.assertTrue(cells["C10"].startswith("=MIS.KPI("))

    def test_export_spreadsheet_no_comparison(self):
        instance = self.env["mis.report.instance"].create(
            {
                "name": "Spreadsheet MIS simple",
                "report_id": self.report.id,
                "company_id": self.company.id,
                "date_from": "2026-01-01",
                "date_to": "2026-01-31",
                "target_move": "all",
            }
        )
        instance.comparison_mode = False
        data = instance._spreadsheet_data()
        cells = {xc: cell["content"] for xc, cell in data["sheets"][0]["cells"].items()}
        self.assertEqual(cells["B4"], "TRUE")
        self.assertNotIn("B5", cells)
        self.assertEqual(cells["B7"], "=DATE(2026,1,1)")
        self.assertEqual(cells["B8"], "=DATE(2026,1,31)")
