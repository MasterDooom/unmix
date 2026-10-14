"""Permutation-, sign-, and scale-aware source-recovery metrics.

Arrays use ``(n_sources, n_samples)``. Correlation is unitless; SI-SDR is
reported in dB. A constant signal has undefined Pearson correlation, so this
module returns 0.0 for any pair containing a zero-variance signal. SI-SDR
requires a non-zero-energy reference; a zero estimate has SI-SDR ``-inf`` and
an exact scaled reference has ``inf``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import linear_sum_assignment

FloatArray = NDArray[np.float64]


def _signals(values: ArrayLike, name: str) -> FloatArray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 2 or 0 in array.shape:
        raise ValueError(f"{name} must be a non-empty 2D (sources, samples) array.")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must contain only finite values.")
    return array


def source_correlation(reference: ArrayLike, estimate: ArrayLike) -> FloatArray:
    """Return signed Pearson correlations for every reference/estimate pair."""
    references = _signals(reference, "reference")
    estimates = _signals(estimate, "estimate")
    if references.shape[1] != estimates.shape[1]:
        raise ValueError("reference and estimate must have the same sample count.")
    reference_centered = references - references.mean(axis=1, keepdims=True)
    estimate_centered = estimates - estimates.mean(axis=1, keepdims=True)
    numerator = reference_centered @ estimate_centered.T
    denominator = np.linalg.norm(reference_centered, axis=1)[:, None] * np.linalg.norm(
        estimate_centered, axis=1
    )[None, :]
    correlation = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)
    return np.clip(correlation, -1.0, 1.0)


def si_sdr(reference: ArrayLike, estimate: ArrayLike) -> float:
    """Return scale-invariant SDR in dB for one reference/estimate pair.

    The estimate is projected onto the reference, then the target-to-residual
    energy ratio is measured. This differs from correlation: correlation only
    measures linear association, while SI-SDR measures projection error energy.
    """
    reference_array = np.asarray(reference, dtype=np.float64).reshape(-1)
    estimate_array = np.asarray(estimate, dtype=np.float64).reshape(-1)
    if reference_array.size == 0 or reference_array.size != estimate_array.size:
        raise ValueError("reference and estimate must be non-empty and equally long.")
    if not np.isfinite(reference_array).all() or not np.isfinite(estimate_array).all():
        raise ValueError("reference and estimate must contain only finite values.")
    reference_energy = float(reference_array @ reference_array)
    if reference_energy == 0.0:
        raise ValueError("SI-SDR is undefined for a zero-energy reference.")
    target = (float(estimate_array @ reference_array) / reference_energy) * reference_array
    residual = estimate_array - target
    target_energy = float(target @ target)
    residual_energy = float(residual @ residual)
    if target_energy == 0.0:
        return float("-inf")
    if residual_energy == 0.0:
        return float("inf")
    return float(10.0 * np.log10(target_energy / residual_energy))


@dataclass(frozen=True)
class SourceRecovery:
    """Metrics for one optimally matched reference and estimated source."""

    reference_index: int
    estimate_index: int
    correlation: float
    absolute_correlation: float
    si_sdr_db: float


@dataclass(frozen=True)
class RecoveryMetrics:
    """Optimal one-to-one matching and aggregate source-recovery measurements."""

    per_source: tuple[SourceRecovery, ...]
    mean_absolute_correlation: float
    mean_si_sdr_db: float


def evaluate_recovery(reference: ArrayLike, estimate: ArrayLike) -> RecoveryMetrics:
    """Optimally match equal-sized source sets using absolute correlation."""
    references = _signals(reference, "reference")
    estimates = _signals(estimate, "estimate")
    if references.shape != estimates.shape:
        raise ValueError("reference and estimate must have identical (sources, samples) shapes.")
    correlation = source_correlation(references, estimates)
    rows, columns = linear_sum_assignment(-np.abs(correlation))
    per_source = tuple(
        SourceRecovery(
            reference_index=int(row),
            estimate_index=int(column),
            correlation=float(correlation[row, column]),
            absolute_correlation=float(abs(correlation[row, column])),
            si_sdr_db=si_sdr(references[row], estimates[column]),
        )
        for row, column in zip(rows, columns, strict=True)
    )
    sdr_values = np.asarray([item.si_sdr_db for item in per_source])
    return RecoveryMetrics(
        per_source=per_source,
        mean_absolute_correlation=float(np.mean([item.absolute_correlation for item in per_source])),
        mean_si_sdr_db=float(np.mean(sdr_values)),
    )
