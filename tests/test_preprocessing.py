import numpy as np
import pytest

from unmix.preprocessing import center_signals, pca_whiten


def test_center_signals_removes_each_channel_mean() -> None:
    centered, mean = center_signals([[1.0, 3.0, 5.0], [2.0, 4.0, 12.0]])

    np.testing.assert_allclose(centered.mean(axis=1), 0.0, atol=1e-15)
    np.testing.assert_allclose(mean[:, 0], [3.0, 6.0])


def test_pca_whiten_produces_identity_covariance() -> None:
    rng = np.random.default_rng(12)
    latent = rng.normal(size=(3, 6000))
    signals = np.array([[1.0, 0.3, -0.2], [0.2, 1.4, 0.5], [-0.4, 0.1, 1.1]]) @ latent

    result = pca_whiten(signals)

    np.testing.assert_allclose(
        result.whitened @ result.whitened.T / signals.shape[1], np.eye(3), atol=1e-10
    )
    np.testing.assert_allclose(
        result.dewhitening_matrix @ result.whitened + result.mean, signals, atol=1e-10
    )


def test_pca_whiten_is_stable_under_uniform_rescaling() -> None:
    rng = np.random.default_rng(4)
    signals = np.array([[1.0, 0.2], [-0.4, 1.1]]) @ rng.normal(size=(2, 4000))

    result = pca_whiten(signals * 1e100)

    np.testing.assert_allclose(
        result.whitened @ result.whitened.T / signals.shape[1], np.eye(2), atol=1e-10
    )


def test_pca_whiten_can_retain_the_full_rank_subspace_of_overdetermined_data() -> None:
    rng = np.random.default_rng(7)
    latent = rng.normal(size=(2, 4000))
    observations = np.array([[1.0, 0.2], [0.1, 1.2], [0.5, -0.3]]) @ latent

    result = pca_whiten(observations, n_components=2)

    assert result.whitened.shape == (2, 4000)
    np.testing.assert_allclose(result.whitened @ result.whitened.T / 4000, np.eye(2), atol=1e-10)


@pytest.mark.parametrize(
    "signals",
    [np.ones((2, 20)), np.array([[1.0], [2.0]]), np.array([[1.0, np.nan], [2.0, 3.0]]), np.ones(4)],
)
def test_preprocessing_rejects_invalid_or_rank_deficient_input(signals) -> None:
    with pytest.raises(ValueError):
        pca_whiten(signals)


def test_pca_whiten_rejects_invalid_tolerances() -> None:
    data = np.eye(2)[:, :2]
    with pytest.raises(ValueError):
        pca_whiten(data, rtol=-1.0)
    with pytest.raises(ValueError):
        pca_whiten(data, atol=np.inf)
    with pytest.raises(ValueError):
        pca_whiten(data, n_components=0)
