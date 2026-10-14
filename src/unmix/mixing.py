"""Linear mixing utilities.

Arrays follow one convention throughout the project:
- sources: (n_sources, n_samples)
- mixing matrix: (n_mixtures, n_sources)
- mixtures: (n_mixtures, n_samples)
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]


def _as_finite_2d(values: ArrayLike, name: str) -> FloatArray:
    """Convert input to a finite, two-dimensional float64 array."""
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError(f"{name} must be a 2D array; got {array.ndim}D.")
    if array.shape[0] == 0 or array.shape[1] == 0:
        raise ValueError(f"{name} must not have an empty dimension.")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must contain only finite values.")
    return array


def mix_sources(sources: ArrayLike, mixing_matrix: ArrayLike) -> FloatArray:
    """Mix independent sources using X = A @ S.

    Parameters
    ----------
    sources:
        Source samples with shape (n_sources, n_samples).
    mixing_matrix:
        Matrix with shape (n_mixtures, n_sources). It must have full column
        rank so every source remains identifiable. For the initial square ICA
        experiments, use an invertible matrix.

    Returns
    -------
    numpy.ndarray
        Mixed recordings with shape (n_mixtures, n_samples).

    Notes
    -----
    This function deliberately does not normalize or clip audio. Those
    operations can change the known mixing relationship and belong in an
    explicit audio/export stage.
    """
    source_array = _as_finite_2d(sources, "sources")
    matrix = _as_finite_2d(mixing_matrix, "mixing_matrix")

    n_sources, _ = source_array.shape
    n_mixtures, matrix_sources = matrix.shape

    if matrix_sources != n_sources:
        raise ValueError(
            "mixing_matrix columns must equal the number of sources "
            f"({matrix_sources} != {n_sources})."
        )
    if n_mixtures < n_sources:
        raise ValueError(
            "Underdetermined mixing is unsupported: provide at least as "
            "many mixtures as sources."
        )
    if np.linalg.matrix_rank(matrix) < n_sources:
        raise ValueError(
            "mixing_matrix must have full column rank to recover all sources."
        )

    return matrix @ source_array
