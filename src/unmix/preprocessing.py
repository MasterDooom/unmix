"""Centering and PCA whitening for channel-by-sample signals.

All arrays use shape ``(n_channels, n_samples)``.  Whitening is deliberately
full-rank: ICA needs one independent component per observed channel, so a
rank-deficient covariance is rejected instead of silently dropping channels.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]


def _as_finite_signals(values: ArrayLike) -> FloatArray:
    """Return finite, non-empty channel-by-sample data as float64."""
    signals = np.asarray(values, dtype=np.float64)
    if signals.ndim != 2:
        raise ValueError(f"signals must be a 2D array; got {signals.ndim}D.")
    if 0 in signals.shape:
        raise ValueError("signals must not have an empty dimension.")
    if signals.shape[1] < 2:
        raise ValueError("signals must contain at least two samples.")
    if not np.isfinite(signals).all():
        raise ValueError("signals must contain only finite values.")
    return signals


def center_signals(signals: ArrayLike) -> tuple[FloatArray, FloatArray]:
    """Center each channel and return ``(centered, channel_means)``.

    ``channel_means`` has shape ``(n_channels, 1)`` so it can be broadcast to
    future data with the same channel order.
    """
    array = _as_finite_signals(signals)
    means = array.mean(axis=1, keepdims=True)
    return array - means, means


@dataclass(frozen=True)
class WhiteningResult:
    """PCA-whitening output and transforms for one observed recording."""

    whitened: FloatArray
    mean: FloatArray
    whitening_matrix: FloatArray
    dewhitening_matrix: FloatArray
    eigenvalues: FloatArray


def pca_whiten(
    signals: ArrayLike,
    *,
    n_components: int | None = None,
    rtol: float | None = None,
    atol: float = 0.0,
) -> WhiteningResult:
    """Center and PCA-whiten full-rank signals using covariance eigendecomposition.

    The covariance is ``X_centered @ X_centered.T / n_samples``.  An
    eigenvalue is considered numerically zero when it is no greater than
    ``max(atol, rtol * largest_eigenvalue)``.  The default ``rtol`` scales
    with both array dimensions and machine precision.  Rank-deficient input
    raises ``ValueError`` rather than producing an unstable inverse square root.
    Set ``n_components`` below the number of channels to retain the leading
    principal subspace, which is required for overdetermined ICA mixtures.
    """
    if rtol is None:
        rtol = np.finfo(np.float64).eps
    if not np.isfinite(rtol) or rtol < 0:
        raise ValueError("rtol must be a finite, non-negative number.")
    if not np.isfinite(atol) or atol < 0:
        raise ValueError("atol must be a finite, non-negative number.")

    centered, mean = center_signals(signals)
    n_channels, n_samples = centered.shape
    if n_components is None:
        n_components = n_channels
    if not isinstance(n_components, int) or not 1 <= n_components <= n_channels:
        raise ValueError("n_components must be an integer between 1 and the number of channels.")
    covariance = (centered @ centered.T) / n_samples
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    largest = float(eigenvalues[-1])
    threshold = max(atol, rtol * max(n_channels, n_samples) * largest)

    selected_values = eigenvalues[-n_components:]
    selected_vectors = eigenvectors[:, -n_components:]
    if largest <= threshold or np.any(selected_values <= threshold):
        raise ValueError(
            "signal covariance is numerically rank-deficient; "
            f"smallest retained eigenvalue={selected_values[0]:.3e}, threshold={threshold:.3e}."
        )

    inverse_sqrt = np.diag(1.0 / np.sqrt(selected_values))
    sqrt = np.diag(np.sqrt(selected_values))
    whitening_matrix = inverse_sqrt @ selected_vectors.T
    dewhitening_matrix = selected_vectors @ sqrt
    whitened = whitening_matrix @ centered

    if not np.isfinite(whitened).all():
        raise FloatingPointError("PCA whitening produced non-finite values.")

    return WhiteningResult(
        whitened=whitened,
        mean=mean,
        whitening_matrix=whitening_matrix,
        dewhitening_matrix=dewhitening_matrix,
        eigenvalues=selected_values,
    )
