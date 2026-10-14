"""Interval, bootstrap and agreement statistics for the Title II study's human-review summary.

Standard library only. The definitions follow the draft analysis plan of the study
(``studies/2026-07-title-ii-annex-i-whitepaper-study/analysis-plan.md``, sections 8 to 10):

- the Wilson score interval with z = 1.959964;
- the Clopper-Pearson exact interval, found by bisection on the binomial tail probabilities;
- a cluster percentile bootstrap: each replicate draws as many clusters as the set has, with
  replacement, pools their counts and recomputes the proportion; replicates whose denominator is
  0 are dropped and counted;
- for two reviewers: raw agreement, Cohen's kappa, PABAK and Gwet's AC1.

A value that is undefined (a zero denominator, an empty set) is returned as ``None`` together
with a reason, never as NaN and never as an exception, so the summary JSON stays valid.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

CONFIDENCE_LEVEL = 0.95
ALPHA = 1 - CONFIDENCE_LEVEL
# analysis-plan.md section 9 fixes z to six decimals. R's qnorm(0.975) is 1.959963984540054; the
# difference moves a Wilson bound by less than 1e-8.
WILSON_Z = 1.959964
BOOTSTRAP_QUANTILE_METHOD = (
    "linear interpolation between order statistics (Hyndman and Fan 1996, type 7, the default of "
    "R's quantile() and numpy.percentile) at 0.025 and 0.975"
)


@dataclass(frozen=True)
class Counts:
    """Confusion-matrix counts of one set of evaluable cells."""

    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    def __add__(self, other: Counts) -> Counts:
        return Counts(self.tp + other.tp, self.fp + other.fp, self.fn + other.fn, self.tn + other.tn)

    def as_dict(self) -> dict[str, int]:
        return {"tp": self.tp, "fp": self.fp, "fn": self.fn, "tn": self.tn}


@dataclass(frozen=True)
class Proportion:
    """A proportion of the confusion matrix: its numerator, denominator and their names."""

    name: str
    numerator: Callable[[Counts], int]
    denominator: Callable[[Counts], int]
    denominator_label: str
    empty_reason: str


PROPORTIONS: tuple[Proportion, ...] = (
    Proportion(
        "precision",
        lambda c: c.tp,
        lambda c: c.tp + c.fp,
        "TP + FP",
        "no detector-flagged cell is labelled present or missing",
    ),
    Proportion(
        "recall",
        lambda c: c.tp,
        lambda c: c.tp + c.fn,
        "TP + FN",
        "no cell is labelled missing (the reviewer identified no gap)",
    ),
    Proportion(
        "specificity",
        lambda c: c.tn,
        lambda c: c.tn + c.fp,
        "TN + FP",
        "no cell is labelled present",
    ),
)
PROPORTION_NAMES: tuple[str, ...] = tuple(proportion.name for proportion in PROPORTIONS)


def undefined_reason(proportion: Proportion, counts: Counts) -> str | None:
    """Why ``proportion`` is undefined for ``counts``, or None if it is defined."""
    if proportion.denominator(counts) == 0:
        return f"{proportion.denominator_label} = 0: {proportion.empty_reason}"
    return None


def wilson_interval(successes: int, n: int, z: float = WILSON_Z) -> tuple[float, float] | None:
    """Wilson score interval for ``successes`` of ``n``; None when ``n`` is 0.

    Wilson (1927), J. Am. Stat. Assoc. 22:209-212. The bounds are clipped to [0, 1], and they are
    exactly 0 for 0 successes and exactly 1 for ``n`` successes, where floating point arithmetic
    would otherwise leave a residue.
    """
    _check_binomial(successes, n)
    if n == 0:
        return None
    p = successes / n
    z2 = z * z
    denominator = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denominator
    half_width = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denominator
    lower = 0.0 if successes == 0 else max(0.0, centre - half_width)
    upper = 1.0 if successes == n else min(1.0, centre + half_width)
    return lower, upper


def clopper_pearson_interval(successes: int, n: int, alpha: float = ALPHA) -> tuple[float, float] | None:
    """Clopper-Pearson exact interval; None when ``n`` is 0.

    Clopper and Pearson (1934), Biometrika 26:404-413. The lower bound is the p at which
    P(X >= successes) = alpha/2, the upper bound the p at which P(X <= successes) = alpha/2, for X
    binomial(n, p). Both are found by bisection to the resolution of a double.
    """
    _check_binomial(successes, n)
    if n == 0:
        return None
    target = alpha / 2
    lower = (
        0.0
        if successes == 0
        else _bisect(lambda p: 1 - _binomial_cdf(successes - 1, n, p) - target, increasing=True)
    )
    upper = (
        1.0
        if successes == n
        else _bisect(lambda p: _binomial_cdf(successes, n, p) - target, increasing=False)
    )
    return lower, upper


def quantile_type7(sorted_values: Sequence[float], probability: float) -> float:
    """Sample quantile by linear interpolation between order statistics (Hyndman-Fan type 7)."""
    if not sorted_values:
        raise ValueError("no values")
    if not 0 <= probability <= 1:
        raise ValueError(f"probability {probability} is outside [0, 1]")
    position = (len(sorted_values) - 1) * probability
    below = math.floor(position)
    above = min(below + 1, len(sorted_values) - 1)
    return sorted_values[below] + (position - below) * (sorted_values[above] - sorted_values[below])


def cluster_bootstrap(
    clusters: Sequence[Counts],
    *,
    replicates: int,
    seed: int,
    level: float = CONFIDENCE_LEVEL,
) -> dict[str, dict[str, Any]]:
    """Percentile bootstrap of every proportion in ``PROPORTIONS`` over ``clusters``.

    ``random.Random(seed)`` drives the draws, so the result depends only on the clusters, their
    order, ``replicates`` and ``seed``. Every replicate draws ``len(clusters)`` clusters with
    replacement (``randrange``) and pools their counts; all proportions are computed from the same
    draws. A replicate whose denominator is 0 is dropped for that proportion and counted. A
    proportion whose denominator is 0 over all clusters is not resampled at all, because every
    replicate would be dropped.
    """
    if replicates < 1:
        raise ValueError("replicates must be at least 1")
    total = sum(clusters, Counts())
    results: dict[str, dict[str, Any]] = {}
    active = []
    for proportion in PROPORTIONS:
        base = {
            "lower": None,
            "upper": None,
            "replicates": replicates,
            "dropped": None,
            "dropped_fraction": None,
            "clusters": len(clusters),
            "seed": seed,
            "undefined_reason": None,
        }
        reason = "no clusters in the set" if not clusters else undefined_reason(proportion, total)
        if reason:
            base["undefined_reason"] = f"point estimate undefined ({reason}); not resampled"
        else:
            active.append(proportion)
        results[proportion.name] = base
    if not active:
        return results

    rng = random.Random(seed)
    k = len(clusters)
    values: dict[str, list[float]] = {proportion.name: [] for proportion in active}
    for _ in range(replicates):
        tp = fp = fn = tn = 0
        for _ in range(k):
            cluster = clusters[rng.randrange(k)]
            tp += cluster.tp
            fp += cluster.fp
            fn += cluster.fn
            tn += cluster.tn
        draw = Counts(tp, fp, fn, tn)
        for proportion in active:
            denominator = proportion.denominator(draw)
            if denominator:
                values[proportion.name].append(proportion.numerator(draw) / denominator)

    tail = (1 - level) / 2
    for proportion in active:
        kept = sorted(values[proportion.name])
        result = results[proportion.name]
        result["dropped"] = replicates - len(kept)
        result["dropped_fraction"] = result["dropped"] / replicates
        if not kept:
            result["undefined_reason"] = "every replicate had a zero denominator"
            continue
        result["lower"] = quantile_type7(kept, tail)
        result["upper"] = quantile_type7(kept, 1 - tail)
    return results


def agreement(pairs: Sequence[tuple[str, str]], categories: Sequence[str]) -> dict[str, Any]:
    """Agreement between two reviewers who labelled the same cells.

    ``pairs`` holds one (first reviewer, second reviewer) label pair per cell, and ``categories``
    the label categories of the classification (q = ``len(categories)``, at least 2). With
    observed agreement po, the reviewers' marginal proportions p1_k and p2_k, and
    pi_k = (p1_k + p2_k) / 2:

    - Cohen's kappa (Cohen 1960, Educ. Psychol. Meas. 20:37-46): (po - pe) / (1 - pe) with
      pe = sum_k p1_k * p2_k. Undefined (None) when pe = 1, that is when both reviewers gave every
      cell one and the same label;
    - PABAK (Byrt, Bishop and Carlin 1993, J. Clin. Epidemiol. 46:423-429): 2 * po - 1 for two
      categories, generalised to (q * po - 1) / (q - 1), which is the Brennan-Prediger coefficient;
    - Gwet's AC1 (Gwet 2008, Br. J. Math. Stat. Psychol. 61:29-48): (po - pe) / (1 - pe) with
      pe = sum_k pi_k * (1 - pi_k) / (q - 1). Its pe is at most 1/q, so AC1 is always defined.
    """
    if len(categories) < 2 or len(set(categories)) != len(categories):
        raise ValueError("agreement needs at least two distinct categories")
    unknown = sorted({label for pair in pairs for label in pair} - set(categories))
    if unknown:
        raise ValueError(f"labels {unknown} are not among the categories {list(categories)}")
    n = len(pairs)
    result: dict[str, Any] = {
        "cells": n,
        "categories": list(categories),
        "agreements": None,
        "raw_agreement": None,
        "cohen_kappa": None,
        "pabak": None,
        "gwet_ac1": None,
        "undefined_reason": None,
    }
    if n == 0:
        result["undefined_reason"] = "no cells in this comparison"
        return result
    q = len(categories)
    agreements = sum(first == second for first, second in pairs)
    po = agreements / n
    first_share = {category: 0.0 for category in categories}
    second_share = {category: 0.0 for category in categories}
    for first, second in pairs:
        first_share[first] += 1 / n
        second_share[second] += 1 / n
    pe_kappa = sum(first_share[c] * second_share[c] for c in categories)
    pi = {c: (first_share[c] + second_share[c]) / 2 for c in categories}
    pe_ac1 = sum(share * (1 - share) for share in pi.values()) / (q - 1)

    result["agreements"] = agreements
    result["raw_agreement"] = po
    if math.isclose(pe_kappa, 1.0, rel_tol=0.0, abs_tol=1e-12):
        result["undefined_reason"] = (
            "Cohen's kappa is 0/0: both reviewers gave every cell the same single label, so chance "
            "agreement is 1"
        )
    else:
        result["cohen_kappa"] = (po - pe_kappa) / (1 - pe_kappa)
    result["pabak"] = (q * po - 1) / (q - 1)
    result["gwet_ac1"] = (po - pe_ac1) / (1 - pe_ac1)
    return result


def interval_dict(bounds: tuple[float, float] | None, reason: str | None, digits: int) -> dict[str, Any]:
    """``{"lower", "upper", "undefined_reason"}`` with the bounds rounded to ``digits``."""
    if bounds is None:
        return {"lower": None, "upper": None, "undefined_reason": reason or "undefined"}
    return {"lower": round(bounds[0], digits), "upper": round(bounds[1], digits), "undefined_reason": None}


def rounded(values: Mapping[str, Any], digits: int) -> dict[str, Any]:
    """Round every float value of a flat mapping; other values are kept."""
    return {key: round(value, digits) if isinstance(value, float) else value for key, value in values.items()}


def _check_binomial(successes: int, n: int) -> None:
    if n < 0 or successes < 0 or successes > n:
        raise ValueError(f"invalid binomial counts: {successes} of {n}")


def _binomial_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X binomial(n, p), 0 < p < 1, summed in log space so large n cannot overflow."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    log_p = math.log(p)
    log_q = math.log1p(-p)
    log_n = math.lgamma(n + 1)
    total = 0.0
    for i in range(k + 1):
        total += math.exp(log_n - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * log_p + (n - i) * log_q)
    return min(total, 1.0)


def _bisect(function: Callable[[float], float], *, increasing: bool) -> float:
    """The root of a monotone ``function`` on (0, 1), bisected until the interval stops shrinking."""
    low, high = 0.0, 1.0
    for _ in range(200):
        middle = (low + high) / 2
        if middle in (low, high):
            break
        value = function(middle)
        if (value < 0) == increasing:
            low = middle
        else:
            high = middle
    return (low + high) / 2
