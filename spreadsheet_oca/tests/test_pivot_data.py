# Copyright 2025 Ledo Enterprises LLC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Tests for server-side pivot data computation.

These tests verify that _get_pivot_data() produces the same grouping
structure that the Odoo JS PivotModel would produce via read_group.

Run against odoo_test (which has sale, account installed):
  docker exec -i odoo-prod odoo test -d odoo_test \
    --test-tags spreadsheet_oca.TestPivotData --stop-after-init
"""

from odoo.tests import TransactionCase

from ..models.pivot_data import _dimension_to_groupby, _get_pivot_data, _sections


class TestPivotDataHelpers(TransactionCase):
    """Unit tests for the pure-Python helpers (no DB needed)."""

    def test_sections_empty(self):
        self.assertEqual(_sections([]), [[]])

    def test_sections_one(self):
        self.assertEqual(_sections(["a"]), [[], ["a"]])

    def test_sections_two(self):
        self.assertEqual(_sections(["a", "b"]), [[], ["a"], ["a", "b"]])

    def test_dimension_no_granularity(self):
        self.assertEqual(
            _dimension_to_groupby({"fieldName": "partner_id"}), "partner_id"
        )

    def test_dimension_with_granularity(self):
        self.assertEqual(
            _dimension_to_groupby({"fieldName": "date_order", "granularity": "month"}),
            "date_order:month",
        )


class TestPivotData(TransactionCase):
    """Integration tests using res.partner (always available, no demo needed)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a handful of partners in different countries to group by
        cls.country_be = cls.env.ref("base.be")
        cls.country_us = cls.env.ref("base.us")
        cls.partners = cls.env["res.partner"].create(
            [
                {"name": "Alpha", "country_id": cls.country_be.id, "is_company": True},
                {"name": "Beta", "country_id": cls.country_be.id, "is_company": True},
                {"name": "Gamma", "country_id": cls.country_us.id, "is_company": True},
                {"name": "Delta", "country_id": cls.country_us.id, "is_company": False},
            ]
        )
        cls.domain = [("id", "in", cls.partners.ids)]

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _run(self, row_dims, col_dims, measures):
        return _get_pivot_data(
            self.env,
            "res.partner",
            self.domain,
            {},
            row_dims,
            col_dims,
            measures,
        )

    def _groups_for(self, result, row_prefix, col_prefix):
        """Return groups matching the given row/col groupby prefix."""
        return [
            g
            for g in result["groups"]
            if g["rowGroupBy"] == row_prefix and g["colGroupBy"] == col_prefix
        ]

    # ── Grand-total (no groupby) ────────────────────────────────────────────

    def test_grand_total_count(self):
        """With no dims, one group with count = number of partners."""
        result = self._run([], [], [{"fieldName": "__count"}])
        groups = self._groups_for(result, [], [])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["count"], 4)

    # ── Single row groupby ──────────────────────────────────────────────────

    def test_row_groupby_country(self):
        """Row groupby country_id → one group per country + grand total."""
        row_dims = [{"fieldName": "country_id"}]
        result = self._run(row_dims, [], [{"fieldName": "__count"}])

        # Grand total (rowGroupBy=[], colGroupBy=[])
        totals = self._groups_for(result, [], [])
        self.assertEqual(len(totals), 1)
        self.assertEqual(totals[0]["count"], 4)

        # Per-country groups (rowGroupBy=["country_id"], colGroupBy=[])
        country_groups = self._groups_for(result, ["country_id"], [])
        self.assertEqual(len(country_groups), 2)
        counts_by_country = {g["rowValues"][0]: g["count"] for g in country_groups}
        self.assertEqual(counts_by_country[self.country_be.id], 2)
        self.assertEqual(counts_by_country[self.country_us.id], 2)

    # ── Row + col groupby ───────────────────────────────────────────────────

    def test_row_and_col_groupby(self):
        """Row=country_id, Col=is_company → 2×2 cell values."""
        row_dims = [{"fieldName": "country_id"}]
        col_dims = [{"fieldName": "is_company"}]
        result = self._run(row_dims, col_dims, [{"fieldName": "__count"}])

        # Divisors: ([], []) ([], [is_company])
        # ([country_id], []) ([country_id], [is_company])
        # → 4 divisors, each producing N read_group rows
        divisor_keys = {
            (tuple(g["rowGroupBy"]), tuple(g["colGroupBy"])) for g in result["groups"]
        }
        self.assertIn(((), ()), divisor_keys)
        self.assertIn(((), ("is_company",)), divisor_keys)
        self.assertIn((("country_id",), ()), divisor_keys)
        self.assertIn((("country_id",), ("is_company",)), divisor_keys)

        # BE / is_company=True  →  Alpha + Beta = 2
        cell_groups = self._groups_for(result, ["country_id"], ["is_company"])
        be_company = [
            g
            for g in cell_groups
            if g["rowValues"] == [self.country_be.id] and g["colValues"] == [True]
        ]
        self.assertEqual(len(be_company), 1)
        self.assertEqual(be_company[0]["count"], 2)

        # US / is_company=False  →  Delta = 1
        us_individual = [
            g
            for g in cell_groups
            if g["rowValues"] == [self.country_us.id] and g["colValues"] == [False]
        ]
        self.assertEqual(len(us_individual), 1)
        self.assertEqual(us_individual[0]["count"], 1)

    # ── Return structure ────────────────────────────────────────────────────

    def test_return_fields_metadata(self):
        """Result includes fields metadata for all used fields."""
        row_dims = [{"fieldName": "country_id"}]
        result = self._run(row_dims, [], [{"fieldName": "__count"}])
        self.assertIn("country_id", result["fields"])
        self.assertEqual(result["fields"]["country_id"]["type"], "many2one")

    def test_return_dimensions_and_specs(self):
        """Result echoes back row/col dims and measure specs."""
        row_dims = [{"fieldName": "country_id"}]
        measures = [{"fieldName": "__count"}]
        result = self._run(row_dims, [], measures)
        self.assertEqual(result["rowDimensions"], row_dims)
        self.assertEqual(result["colDimensions"], [])
        self.assertEqual(result["measureSpecs"], ["__count"])

    # ── Domain filtering ────────────────────────────────────────────────────

    def test_domain_filters_correctly(self):
        """Domain restricts records — only BE partners."""
        be_domain = [
            ("id", "in", self.partners.ids),
            ("country_id", "=", self.country_be.id),
        ]
        result = _get_pivot_data(
            self.env, "res.partner", be_domain, {}, [], [], [{"fieldName": "__count"}]
        )
        totals = self._groups_for(result, [], [])
        self.assertEqual(totals[0]["count"], 2)
