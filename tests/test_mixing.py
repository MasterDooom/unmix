import numpy as np
import pytest

from unmix.mixing import mix_sources


def test_mix_sources_matches_matrix_product() -> None:
    sources = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    matrix = np.array([[1.0, 0.5], [0.25, 2.0]])
    expected = matrix @ sources

    actual = mix_sources(sources, matrix)

    np.testing.assert_allclose(actual, expected)
    assert actual.shape == (2, 3)


def test_mix_sources_supports_more_mixtures_than_sources() -> None:
    sources = np.array([[1.0, 2.0], [3.0, 4.0]])
    matrix = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])

    actual = mix_sources(sources, matrix)

    assert actual.shape == (3, 2)
    np.testing.assert_allclose(actual[2], sources.sum(axis=0))


@pytest.mark.parametrize(
    ("sources", "matrix"),
    [
        (np.array([1.0, 2.0]), np.eye(2)),
        (np.ones((2, 3)), np.ones((2, 2))),
        (np.ones((2, 3)), np.ones((1, 2))),
        (np.ones((2, 3)), np.array([[1.0, 2.0], [2.0, 4.0]])),
        (np.array([[1.0, np.nan], [2.0, 3.0]]), np.eye(2)),
        (np.ones((2, 3)), np.array([[1.0, 0.0], [0.0, np.inf]])),
        (np.empty((0, 3)), np.eye(2)),
    ],
)
def test_mix_sources_rejects_invalid_inputs(sources, matrix) -> None:
    with pytest.raises(ValueError):
        mix_sources(sources, matrix)
