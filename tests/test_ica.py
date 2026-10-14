import numpy as np
import pytest

from unmix.ica import FastICAConvergenceError, fastica
from unmix.mixing import mix_sources


def _synthetic_sources(n_samples: int = 12000, seed: int = 91) -> np.ndarray:
    rng = np.random.default_rng(seed)
    sources = np.vstack(
        [
            rng.laplace(size=n_samples),
            rng.uniform(-1.0, 1.0, size=n_samples),
            rng.standard_t(df=5, size=n_samples),
        ]
    )
    return (sources - sources.mean(axis=1, keepdims=True)) / sources.std(axis=1, keepdims=True)


def _best_absolute_correlations(recovered: np.ndarray, expected: np.ndarray) -> np.ndarray:
    correlation = np.abs(np.corrcoef(recovered, expected)[: recovered.shape[0], recovered.shape[0] :])
    remaining = set(range(expected.shape[0]))
    matches = []
    for row in range(recovered.shape[0]):
        column = max(remaining, key=lambda candidate: correlation[row, candidate])
        matches.append(correlation[row, column])
        remaining.remove(column)
    return np.asarray(matches)


@pytest.mark.parametrize(
    ("seed", "mixing_matrix"),
    [
        (91, np.array([[1.0, 0.4, -0.2], [0.3, 1.2, 0.5], [-0.5, 0.2, 1.1]])),
        (202, np.array([[1.1, -0.3, 0.4], [0.2, 0.9, 0.6], [0.5, 0.1, 1.3]])),
    ],
)
def test_fastica_recovers_independent_synthetic_sources(seed: int, mixing_matrix: np.ndarray) -> None:
    sources = _synthetic_sources(8000, seed)
    mixtures = mix_sources(sources, mixing_matrix)

    result = fastica(mixtures, random_state=7, tol=1e-7)

    assert result.converged
    assert result.sources.shape == mixtures.shape
    assert result.n_iter <= 500
    assert np.all(_best_absolute_correlations(result.sources, sources) > 0.98)


def test_fastica_is_deterministic_for_a_seed() -> None:
    mixtures = mix_sources(_synthetic_sources(5000), np.array([[1.0, 0.2, 0.4], [0.3, 1.0, -0.1], [0.2, 0.5, 1.0]]))

    first = fastica(mixtures, random_state=5)
    second = fastica(mixtures, random_state=5)

    np.testing.assert_allclose(first.sources, second.sources)
    np.testing.assert_allclose(first.unmixing_matrix, second.unmixing_matrix)


def test_fastica_recovers_overdetermined_mixtures_when_component_count_is_given() -> None:
    sources = _synthetic_sources(8000, seed=301)[:2]
    matrix = np.array([[1.0, 0.3], [0.2, 1.1], [0.6, -0.4]])

    result = fastica(mix_sources(sources, matrix), n_components=2, random_state=4, tol=1e-7)

    assert result.sources.shape == sources.shape
    assert result.unmixing_matrix.shape == (2, 3)
    assert np.all(_best_absolute_correlations(result.sources, sources) > 0.98)


def test_fastica_reports_nonconvergence() -> None:
    mixtures = mix_sources(_synthetic_sources(1000), np.eye(3))

    with pytest.raises(FastICAConvergenceError):
        fastica(mixtures, max_iter=1, tol=1e-16, random_state=3)
    result = fastica(mixtures, max_iter=1, tol=1e-16, random_state=3, raise_on_nonconvergence=False)
    assert not result.converged
    assert result.n_iter == 1
    assert np.isfinite(result.max_change)


@pytest.mark.parametrize(
    "mixtures",
    [np.ones((2, 30)), np.array([[1.0, np.inf], [2.0, 3.0]]), np.ones(5)],
)
def test_fastica_rejects_invalid_or_rank_deficient_mixtures(mixtures) -> None:
    with pytest.raises(ValueError):
        fastica(mixtures)


def test_fastica_rejects_invalid_configuration() -> None:
    mixtures = _synthetic_sources(1000)
    with pytest.raises(ValueError):
        fastica(mixtures, max_iter=0)
    with pytest.raises(ValueError):
        fastica(mixtures, tol=0.0)
    with pytest.raises(ValueError):
        fastica(mixtures, random_state=1.5)
