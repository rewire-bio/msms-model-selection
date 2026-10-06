"""Ranking metrics with explicit tie handling and molecule-grouped bootstrap."""

from __future__ import annotations

import numpy as np


def rank_counts(scores: np.ndarray, target_index: int = 0,
                weights: np.ndarray | None = None) -> tuple[float, float]:
    """Return (b, t): weighted count of decoys scoring above / equal to the target.

    `weights` gives each pool entry a multiplicity (used to reproduce released
    metrics on candidate lists that contain repeated structures).
    """
    scores = np.asarray(scores)
    w = np.ones(len(scores)) if weights is None else np.asarray(weights, dtype=float)
    target = scores[target_index]
    decoy = np.ones(len(scores), dtype=bool)
    decoy[target_index] = False
    b = float(w[decoy & (scores > target)].sum())
    t = float(w[decoy & (scores == target)].sum())
    return b, t


def recall_expected(b: np.ndarray, t: np.ndarray, k: int) -> np.ndarray:
    """Recall@k under uniform random tie-breaking."""
    return np.clip((k - np.asarray(b)) / (np.asarray(t) + 1.0), 0.0, 1.0)


def recall_strict(b: np.ndarray, t: np.ndarray, k: int) -> np.ndarray:
    """Released rule: every tied decoy ranks ahead of the target."""
    return (np.asarray(b) + np.asarray(t) + 1.0 <= k).astype(float)


def grouped_bootstrap(values: dict[str, np.ndarray], groups: np.ndarray,
                      n_boot: int = 2000, seed: int = 20261004) -> dict[str, np.ndarray]:
    """Bootstrap spectrum-level means, resampling whole groups (molecules).

    Returns, for each key, an array of `n_boot` replicate means. Using the same
    draws for every key makes differences between keys paired.
    """
    groups = np.asarray(groups)
    uniq, inverse = np.unique(groups, return_inverse=True)
    n_groups = len(uniq)
    counts = np.bincount(inverse, minlength=n_groups).astype(float)
    sums = {k: np.bincount(inverse, weights=np.asarray(v, float), minlength=n_groups)
            for k, v in values.items()}
    rng = np.random.default_rng(seed)
    out = {k: np.empty(n_boot) for k in values}
    for i in range(n_boot):
        draw = np.bincount(rng.integers(0, n_groups, n_groups), minlength=n_groups)
        denom = (draw * counts).sum()
        for k in values:
            out[k][i] = (draw * sums[k]).sum() / denom
    return out


def summarise(point: float, replicates: np.ndarray) -> dict[str, float]:
    lo, hi = np.percentile(replicates, [2.5, 97.5])
    return {"estimate": float(point), "ci_low": float(lo), "ci_high": float(hi)}
