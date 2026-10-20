"""Robust, leakage-aware research statistics for Gagarin.

Diagnostics only: no signal generation, no strategy promotion, and PAPER ONLY.
"""
from __future__ import annotations

import math
import random
import statistics
from typing import Sequence


def _finite_series(values: Sequence[float], name: str) -> list[float]:
    out = [float(value) for value in values]
    if not all(math.isfinite(value) for value in out):
        raise ValueError(f"{name} deve contenere solo valori finiti")
    return out


def _circular_block_sample(values: list[float], block_size: int, rng: random.Random) -> list[float]:
    n = len(values)
    sample: list[float] = []
    while len(sample) < n:
        start = rng.randrange(n)
        sample.extend(values[(start + offset) % n] for offset in range(block_size))
    return sample[:n]


def bootstrap_mean_ci(
    returns: Sequence[float],
    confidence: float = 0.95,
    bootstrap_samples: int = 2000,
    block_size: int | None = None,
    seed: int = 17,
    min_sample: int = 20,
) -> dict:
    """Circular moving-block bootstrap percentile CI for the mean return."""
    values = _finite_series(returns, "returns")
    if not 0 < confidence < 1:
        raise ValueError("confidence deve essere tra 0 e 1")
    if bootstrap_samples < 100:
        raise ValueError("bootstrap_samples deve essere almeno 100")
    if len(values) < min_sample:
        return {"status": "INSUFFICIENT_SAMPLE", "n": len(values), "ci_low": None,
                "ci_high": None, "mean": None, "paper_only": True}
    size = block_size if block_size is not None else max(1, round(len(values) ** (1 / 3)))
    if size < 1 or size > len(values):
        raise ValueError("block_size deve essere compreso tra 1 e n")
    rng = random.Random(seed)
    means = [statistics.mean(_circular_block_sample(values, size, rng))
             for _ in range(bootstrap_samples)]
    means.sort()
    alpha = (1 - confidence) / 2
    lo = means[int(alpha * (len(means) - 1))]
    hi = means[int((1 - alpha) * (len(means) - 1))]
    return {
        "status": "OBSERVATION", "n": len(values), "mean": statistics.mean(values),
        "confidence": confidence, "ci_low": lo, "ci_high": hi, "block_size": size,
        "bootstrap_samples": bootstrap_samples, "seed": seed, "paper_only": True,
        "note": "Intervallo bootstrap diagnostico; non garantisce stazionarietà o redditività futura.",
    }


def walk_forward_splits(
    n_samples: int, train_size: int, test_size: int, step: int | None = None,
    expanding: bool = True, gap: int = 0,
) -> list[dict]:
    """Chronological train/test ranges; optional gap/embargo before test folds."""
    if n_samples < 0 or train_size < 1 or test_size < 1 or gap < 0:
        raise ValueError("Dimensioni non valide")
    stride = step if step is not None else test_size
    if stride < 1:
        raise ValueError("step deve essere >= 1")
    splits = []
    test_start = train_size + gap
    while test_start + test_size <= n_samples:
        train_end = test_start - gap
        train_start = 0 if expanding else max(0, train_end - train_size)
        if train_end - train_start < train_size:
            break
        splits.append({
            "train_start": train_start, "train_end": train_end,
            "test_start": test_start, "test_end": test_start + test_size, "gap": gap,
        })
        test_start += stride
    return splits


def bootstrap_superiority_test(
    candidate_returns: Sequence[float], benchmark_returns: Sequence[float],
    candidate_costs: Sequence[float] | None = None,
    benchmark_costs: Sequence[float] | None = None,
    out_of_sample: Sequence[bool] | None = None,
    confidence: float = 0.95, bootstrap_samples: int = 2000,
    block_size: int | None = None, seed: int = 29, min_sample: int = 30,
) -> dict:
    """One-sided block-bootstrap comparison net of costs; not full Hansen SPA."""
    candidate = _finite_series(candidate_returns, "candidate_returns")
    benchmark = _finite_series(benchmark_returns, "benchmark_returns")
    n = len(candidate)
    if len(benchmark) != n:
        raise ValueError("Candidate e benchmark devono avere la stessa lunghezza")
    cc = _finite_series(candidate_costs if candidate_costs is not None else [0.0] * n, "candidate_costs")
    bc = _finite_series(benchmark_costs if benchmark_costs is not None else [0.0] * n, "benchmark_costs")
    mask = list(out_of_sample) if out_of_sample is not None else [True] * n
    if len(cc) != n or len(bc) != n or len(mask) != n:
        raise ValueError("Tutte le serie devono avere la stessa lunghezza")
    if any(value < 0 for value in cc + bc):
        raise ValueError("I costi non possono essere negativi")
    differences = [candidate[i] - cc[i] - benchmark[i] + bc[i] for i in range(n) if mask[i]]
    if not 0 < confidence < 1:
        raise ValueError("confidence deve essere tra 0 e 1")
    if bootstrap_samples < 100:
        raise ValueError("bootstrap_samples deve essere almeno 100")
    if len(differences) < min_sample:
        return {"status": "INSUFFICIENT_OOS_SAMPLE", "n_oos": len(differences),
                "need": min_sample, "mean_net_difference": None, "p_value_one_sided": None,
                "promoted": False, "paper_only": True}
    size = block_size if block_size is not None else max(1, round(len(differences) ** (1 / 3)))
    if size < 1 or size > len(differences):
        raise ValueError("block_size deve essere compreso tra 1 e n_oos")
    observed = statistics.mean(differences)
    centered = [x - observed for x in differences]
    rng = random.Random(seed)
    null_means = [statistics.mean(_circular_block_sample(centered, size, rng))
                  for _ in range(bootstrap_samples)]
    p_value = (1 + sum(value >= observed for value in null_means)) / (bootstrap_samples + 1)
    ci = bootstrap_mean_ci(differences, confidence, bootstrap_samples, size, seed, min_sample)
    return {
        "status": "OOS_EDGE_CANDIDATE" if observed > 0 and p_value < (1 - confidence) else "OOS_EDGE_NOT_DEMONSTRATED",
        "n_oos": len(differences), "mean_net_difference": observed, "confidence": confidence,
        "ci_low": ci["ci_low"], "ci_high": ci["ci_high"], "p_value_one_sided": p_value,
        "block_size": size, "bootstrap_samples": bootstrap_samples, "promoted": False,
        "paper_only": True,
        "note": "Bootstrap diagnostico, non SPA completo; nessuna promozione automatica.",
    }
