"""Symmetric FastICA implemented from scratch for channel-by-sample arrays."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .preprocessing import pca_whiten

FloatArray = NDArray[np.float64]


class FastICAConvergenceError(RuntimeError):
    """Raised when FastICA reaches its iteration limit without converging."""

    def __init__(self, n_iter: int, max_change: float) -> None:
        super().__init__(
            f"FastICA did not converge after {n_iter} iterations "
            f"(maximum component change {max_change:.3e})."
        )
        self.n_iter = n_iter
        self.max_change = max_change


@dataclass(frozen=True)
class FastICAResult:
    """Separated signals plus transforms and convergence diagnostics."""

    sources: FloatArray
    unmixing_matrix: FloatArray
    mean: FloatArray
    n_iter: int
    converged: bool
    max_change: float


def _symmetric_decorrelation(weights: FloatArray) -> FloatArray:
    """Project rows of ``weights`` to an orthonormal basis."""
    gram = weights @ weights.T
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    scale = max(float(eigenvalues[-1]), 1.0)
    threshold = np.finfo(np.float64).eps * weights.shape[0] * scale
    if np.any(eigenvalues <= threshold):
        raise FloatingPointError("FastICA weights became numerically singular.")
    return (eigenvectors * (1.0 / np.sqrt(eigenvalues))) @ eigenvectors.T @ weights


def fastica(
    mixtures: ArrayLike,
    *,
    max_iter: int = 500,
    tol: float = 1e-6,
    random_state: int = 0,
    n_components: int | None = None,
    raise_on_nonconvergence: bool = True,
) -> FastICAResult:
    """Separate full-rank observed mixtures with symmetric FastICA.

    Only ``mixtures`` are accepted, with shape ``(n_channels, n_samples)``.
    The function centers and PCA-whitens them, then applies the parallel
    fixed-point update using ``g(u)=tanh(u)`` and symmetric decorrelation.
    Tanh is bounded, which limits the effect of large samples while retaining
    sensitivity to the non-Gaussian signals ICA identifies.

    Convergence is measured by sign-invariant row alignment between successive
    unmixing matrices.  Set ``raise_on_nonconvergence=False`` to receive the
    last stable iterate and its diagnostics instead of an exception.

    For an overdetermined recording, set ``n_components`` to the expected
    source count. The leading PCA subspace is whitened before ICA; no source
    samples or mixing matrix values are passed to the separator.
    """
    if not isinstance(max_iter, int) or max_iter <= 0:
        raise ValueError("max_iter must be a positive integer.")
    if not np.isfinite(tol) or tol <= 0:
        raise ValueError("tol must be a finite, positive number.")
    if not isinstance(random_state, (int, np.integer)):
        raise ValueError("random_state must be an integer.")

    whitening = pca_whiten(mixtures, n_components=n_components)
    whitened = whitening.whitened
    n_components, n_samples = whitened.shape
    rng = np.random.default_rng(random_state)
    weights = _symmetric_decorrelation(rng.standard_normal((n_components, n_components)))
    max_change = np.inf

    for n_iter in range(1, max_iter + 1):
        projected = weights @ whitened
        nonlinearity = np.tanh(projected)
        derivative = 1.0 - nonlinearity**2
        updated = (nonlinearity @ whitened.T) / n_samples
        updated -= derivative.mean(axis=1, keepdims=True) * weights
        if not np.isfinite(updated).all():
            raise FloatingPointError("FastICA update produced non-finite values.")
        updated = _symmetric_decorrelation(updated)
        max_change = float(np.max(np.abs(np.abs(np.diag(updated @ weights.T)) - 1.0)))
        weights = updated
        if max_change < tol:
            sources = weights @ whitened
            return FastICAResult(
                sources=sources,
                unmixing_matrix=weights @ whitening.whitening_matrix,
                mean=whitening.mean,
                n_iter=n_iter,
                converged=True,
                max_change=max_change,
            )

    sources = weights @ whitened
    result = FastICAResult(
        sources=sources,
        unmixing_matrix=weights @ whitening.whitening_matrix,
        mean=whitening.mean,
        n_iter=max_iter,
        converged=False,
        max_change=max_change,
    )
    if raise_on_nonconvergence:
        raise FastICAConvergenceError(max_iter, max_change)
    return result
