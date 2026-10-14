"""Interval, bootstrap and agreement statistics of the study summary (review_metrics).

Reference values and their sources:

- [R-binom] R package binom, ``binom.confint(x, n, tol = 1e-8)``, methods "exact" (Clopper-Pearson)
  and "wilson", as recorded by statsmodels in
  statsmodels/stats/tests/results/results_proportion.py at commit
  28c2d902e93c54d8615b2e4b60f8b8a3f74ae605 (github.com/statsmodels/statsmodels). R's Wilson
  interval uses z = qnorm(0.975) = 1.959963984540054; the study fixes z = 1.959964, which moves a
  bound by less than 1e-8, so Wilson values are compared to 1e-7.
- [R-binom.test] R ``binom.test(51, 235, 1/6)``, two-sided 95% interval, as recorded in
  statsmodels/stats/tests/test_proportion.py (``test_binom_test``) at the same commit.
- [irrCAC] R package irrCAC 1.4, vignette "overview" (inst/doc/overview.html at
  github.com/cran/irrCAC commit 720ab226e407e238bf85f86e9458b93e7793e8a3): the two-rater table
  ``cont3x3abstractors`` from Gwet (2014), Handbook of Inter-Rater Reliability, 4th ed., with the
  printed outputs of kappa2.table, gwet.ac1.table, bp2.table and pa2.table.
- [hand] values worked out in the comment from the definitions cited in review_metrics.
"""

from __future__ import annotations

import math
import random

import pytest

from micar_linter.review_metrics import (
    PROPORTION_NAMES,
    WILSON_Z,
    Counts,
    agreement,
    clopper_pearson_interval,
    cluster_bootstrap,
    quantile_type7,
    wilson_interval,
)

# [R-binom]: (x, n): (lower, upper)
R_WILSON = {
    (18, 20): (0.6989663547715128, 0.972133518786232),
    (4, 20): (0.0806576625797981, 0.4160174322518935),
    (4, 200): (0.00780442641634947, 0.05028708690582643),
    (190, 200): (0.910421851861224, 0.972617354399236),
}
R_EXACT = {
    (18, 20): (0.6830172859809176, 0.9876514728297052),
    (4, 20): (0.05733399705003284, 0.436614002996668),
    (4, 200): (0.005475565879556443, 0.05041360908989634),
    (190, 200): (0.9099724622986486, 0.975765834527891),
}


@pytest.mark.parametrize(("cell", "expected"), R_WILSON.items())
def test_wilson_matches_r_binom(cell, expected):
    assert wilson_interval(*cell) == pytest.approx(expected, abs=1e-7)


@pytest.mark.parametrize(("cell", "expected"), R_EXACT.items())
def test_clopper_pearson_matches_r_binom(cell, expected):
    assert clopper_pearson_interval(*cell) == pytest.approx(expected, abs=1e-9)


def test_clopper_pearson_matches_r_binom_test():
    # [R-binom.test]
    assert clopper_pearson_interval(51, 235) == pytest.approx(
        (0.1660633298083073, 0.2752683640289254), abs=1e-9
    )


def test_boundary_counts():
    # [R-binom] (0, 30) and (30, 30), printed to 8 decimals; R clips the bounds to [0, 1].
    assert wilson_interval(0, 30) == pytest.approx((0.0, 0.11351339), abs=1e-7)
    assert wilson_interval(30, 30) == pytest.approx((0.8864866, 1.0), abs=1e-7)
    assert clopper_pearson_interval(0, 30) == pytest.approx((0.0, 0.11570331), abs=1e-7)
    assert clopper_pearson_interval(30, 30) == pytest.approx((0.8842967, 1.0), abs=1e-7)
    # [hand] For x = 0 the exact upper bound solves (1 - p)^n = 0.025, and for x = n the lower
    # bound solves p^n = 0.025 (Clopper and Pearson 1934).
    for n in (1, 9, 20, 135):
        assert clopper_pearson_interval(0, n) == pytest.approx((0.0, 1 - 0.025 ** (1 / n)), abs=1e-12)
        assert clopper_pearson_interval(n, n) == pytest.approx((0.025 ** (1 / n), 1.0), abs=1e-12)
    # The bounds at the boundary are exact, not floating-point residues.
    assert wilson_interval(0, 7)[0] == 0.0
    assert wilson_interval(7, 7)[1] == 1.0


def test_single_cell_and_empty_denominator():
    # [hand] n = 1, x = 0: centre and half-width are both (z^2 / 2) / (1 + z^2), so the Wilson
    # interval is [0, z^2 / (1 + z^2)]; by symmetry x = 1 gives [1 / (1 + z^2), 1].
    z2 = WILSON_Z**2
    assert wilson_interval(0, 1) == pytest.approx((0.0, z2 / (1 + z2)), abs=1e-12)
    assert wilson_interval(1, 1) == pytest.approx((1 / (1 + z2), 1.0), abs=1e-12)
    assert clopper_pearson_interval(1, 1) == pytest.approx((0.025, 1.0), abs=1e-12)
    assert clopper_pearson_interval(0, 1) == pytest.approx((0.0, 0.975), abs=1e-12)
    # 0/0 is undefined: None, never NaN and never an exception.
    assert wilson_interval(0, 0) is None
    assert clopper_pearson_interval(0, 0) is None
    for bad in ((3, 2), (-1, 2), (0, -1)):
        with pytest.raises(ValueError):
            wilson_interval(*bad)
        with pytest.raises(ValueError):
            clopper_pearson_interval(*bad)


def test_quantile_type7():
    # [hand] Hyndman and Fan (1996), definition 7: h = (n - 1) p, then interpolate between the
    # order statistics floor(h) and floor(h) + 1 (0-based). For [1, 2, 3, 4]: p = 0.025 gives
    # h = 0.075 and 1.075; p = 0.975 gives h = 2.925 and 3.925.
    values = [1.0, 2.0, 3.0, 4.0]
    assert quantile_type7(values, 0.025) == pytest.approx(1.075)
    assert quantile_type7(values, 0.975) == pytest.approx(3.925)
    assert quantile_type7(values, 0.0) == 1.0
    assert quantile_type7(values, 1.0) == 4.0
    assert quantile_type7([0.5], 0.975) == 0.5
    with pytest.raises(ValueError):
        quantile_type7([], 0.5)
    with pytest.raises(ValueError):
        quantile_type7(values, 1.5)


def _replay(clusters: list[Counts], replicates: int, seed: int) -> dict[str, tuple[float, float, int]]:
    """An independent restatement of the documented procedure, for comparison."""
    rng = random.Random(seed)
    draws = {"precision": [], "recall": [], "specificity": []}
    for _ in range(replicates):
        pooled = Counts()
        for _ in range(len(clusters)):
            pooled = pooled + clusters[rng.randrange(len(clusters))]
        for name, (num, den) in {
            "precision": (pooled.tp, pooled.tp + pooled.fp),
            "recall": (pooled.tp, pooled.tp + pooled.fn),
            "specificity": (pooled.tn, pooled.tn + pooled.fp),
        }.items():
            if den:
                draws[name].append(num / den)
    result = {}
    for name, values in draws.items():
        values.sort()
        result[name] = (
            quantile_type7(values, 0.025),
            quantile_type7(values, 0.975),
            replicates - len(values),
        )
    return result


def test_bootstrap_follows_the_documented_procedure_and_is_seeded():
    clusters = [Counts(2, 1, 0, 12), Counts(0, 0, 1, 14), Counts(1, 0, 2, 12), Counts(3, 1, 1, 10)]
    first = cluster_bootstrap(clusters, replicates=500, seed=20261014)
    again = cluster_bootstrap(clusters, replicates=500, seed=20261014)
    other = cluster_bootstrap(clusters, replicates=500, seed=1)
    assert first == again
    assert first != other
    replay = _replay(clusters, 500, 20261014)
    for name in PROPORTION_NAMES:
        result = first[name]
        assert (result["lower"], result["upper"], result["dropped"]) == pytest.approx(replay[name])
        assert result["seed"] == 20261014
        assert result["replicates"] == 500
        assert result["clusters"] == 4
        assert result["undefined_reason"] is None


def test_bootstrap_counts_dropped_replicates():
    # Only the first of three clusters has a flagged cell. A replicate misses it with probability
    # (2/3)^3 = 0.296, and then has no precision; when present, precision is 1.
    clusters = [Counts(tp=1), Counts(tn=1), Counts(tn=1)]
    result = cluster_bootstrap(clusters, replicates=10_000, seed=20261014)["precision"]
    assert 0.27 < result["dropped_fraction"] < 0.32
    assert result["dropped"] == round(result["dropped_fraction"] * 10_000)
    assert (result["lower"], result["upper"]) == (1.0, 1.0)


def test_bootstrap_edge_cases():
    # One cluster, or identical clusters: every replicate equals the pooled estimate.
    single = cluster_bootstrap([Counts(3, 1, 1, 5)], replicates=100, seed=7)
    assert (single["precision"]["lower"], single["precision"]["upper"]) == (0.75, 0.75)
    same = cluster_bootstrap([Counts(1, 1, 0, 3)] * 5, replicates=100, seed=7)
    assert (same["precision"]["lower"], same["precision"]["upper"]) == (0.5, 0.5)
    # 0/0 point estimate: not resampled, reason given, nothing dropped is invented.
    empty = cluster_bootstrap([Counts(tn=4), Counts(tn=2)], replicates=100, seed=7)
    for name in ("precision", "recall"):
        assert empty[name]["lower"] is None
        assert empty[name]["dropped"] is None
        assert "point estimate undefined" in empty[name]["undefined_reason"]
    assert empty["specificity"]["lower"] == 1.0
    none = cluster_bootstrap([], replicates=100, seed=7)
    assert all(
        none[name]["undefined_reason"].startswith("point estimate undefined (no clusters") for name in none
    )
    with pytest.raises(ValueError):
        cluster_bootstrap([Counts(1)], replicates=0, seed=7)


def _table_pairs(table: dict[tuple[str, str], int]) -> list[tuple[str, str]]:
    return [pair for pair, count in table.items() for _ in range(count)]


def test_agreement_matches_irrcac_reference_table():
    # [irrCAC] cont3x3abstractors: rows are abstractor 1, columns abstractor 2.
    #            Ectopic AIU NIU
    #   Ectopic       13   0   0
    #   AIU            0  20   7
    #   NIU            0   4  56
    # Printed: Cohen's Kappa 0.7964094; Gwet's AC1 0.8493305; Brennan-Prediger 0.835 (PABAK for
    # q = 3 categories); Percent Agreement 0.89.
    pairs = _table_pairs({("E", "E"): 13, ("A", "A"): 20, ("A", "N"): 7, ("N", "A"): 4, ("N", "N"): 56})
    result = agreement(pairs, ["E", "A", "N"])
    assert result["cells"] == 100
    assert result["agreements"] == 89
    assert result["raw_agreement"] == pytest.approx(0.89)
    assert result["cohen_kappa"] == pytest.approx(0.7964094, abs=1e-7)
    assert result["gwet_ac1"] == pytest.approx(0.8493305, abs=1e-7)
    assert result["pabak"] == pytest.approx(0.835, abs=1e-12)


def test_binary_agreement_and_the_kappa_paradox():
    # [hand] 2x2 table, 50 cells: present/present 20, present/missing 5, missing/present 10,
    # missing/missing 15. po = 35/50 = 0.7; marginals (0.5, 0.5) and (0.6, 0.4), so
    # pe = 0.5 * 0.6 + 0.5 * 0.4 = 0.5 and kappa = 0.2 / 0.5 = 0.4; PABAK = 2 * 0.7 - 1 = 0.4;
    # pi = (0.55, 0.45), pe(AC1) = 2 * 0.55 * 0.45 / 1 = 0.495, AC1 = 0.205 / 0.505.
    pairs = _table_pairs(
        {
            ("present", "present"): 20,
            ("present", "missing"): 5,
            ("missing", "present"): 10,
            ("missing", "missing"): 15,
        }
    )
    result = agreement(pairs, ["present", "missing"])
    assert result["cohen_kappa"] == pytest.approx(0.4)
    assert result["pabak"] == pytest.approx(0.4)
    assert result["gwet_ac1"] == pytest.approx(0.205 / 0.505)
    # [hand] High agreement on a dominant label: 45 present/present, 3 present/missing,
    # 2 missing/present. po = 0.9; marginals (0.96, 0.04) and (0.94, 0.06);
    # pe = 0.96 * 0.94 + 0.04 * 0.06 = 0.9048, kappa = (0.9 - 0.9048) / 0.0952 < 0, while
    # pi = (0.95, 0.05), pe(AC1) = 0.095 and AC1 = 0.805 / 0.905.
    skewed = _table_pairs({("present", "present"): 45, ("present", "missing"): 3, ("missing", "present"): 2})
    paradox = agreement(skewed, ["present", "missing"])
    assert paradox["cohen_kappa"] == pytest.approx((0.9 - 0.9048) / 0.0952)
    assert paradox["gwet_ac1"] == pytest.approx(0.805 / 0.905)
    assert paradox["pabak"] == pytest.approx(0.8)


def test_agreement_edge_cases():
    labels = ["present", "missing"]
    # All agree on one label: kappa is 0/0 and reported as undefined; AC1 and PABAK are 1.
    unanimous = agreement([("present", "present")] * 12, labels)
    assert unanimous["cohen_kappa"] is None
    assert "0/0" in unanimous["undefined_reason"]
    assert unanimous["gwet_ac1"] == 1.0
    assert unanimous["pabak"] == 1.0
    assert unanimous["raw_agreement"] == 1.0
    # All agree across both labels: every coefficient is 1.
    perfect = agreement([("present", "present"), ("missing", "missing")] * 3, labels)
    assert (perfect["cohen_kappa"], perfect["gwet_ac1"], perfect["pabak"]) == pytest.approx((1.0, 1.0, 1.0))
    # n = 1.
    one_agree = agreement([("missing", "missing")], labels)
    assert one_agree["cohen_kappa"] is None
    assert one_agree["gwet_ac1"] == 1.0
    one_disagree = agreement([("present", "missing")], labels)
    assert one_disagree["cohen_kappa"] == 0.0
    assert one_disagree["gwet_ac1"] == pytest.approx(-1.0)
    assert one_disagree["pabak"] == pytest.approx(-1.0)
    # n = 0: nothing is defined, and the reason says so.
    nothing = agreement([], labels)
    assert nothing["cells"] == 0
    assert all(nothing[key] is None for key in ("raw_agreement", "cohen_kappa", "pabak", "gwet_ac1"))
    assert nothing["undefined_reason"] == "no cells in this comparison"
    # No result is ever NaN.
    for result in (unanimous, perfect, one_agree, one_disagree, nothing):
        assert not any(isinstance(value, float) and math.isnan(value) for value in result.values())
    with pytest.raises(ValueError):
        agreement([("present", "pending")], labels)
    with pytest.raises(ValueError):
        agreement([("present", "present")], ["present"])
