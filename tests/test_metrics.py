import numpy as np
import pytest

from unmix.metrics import evaluate_recovery, si_sdr, source_correlation


def test_metrics_match_permuted_signed_and_scaled_sources() -> None:
    reference = np.array([[1.0, -1.0, 2.0, -2.0], [2.0, 1.0, -1.0, -2.0]])
    estimate = np.vstack([-3.0 * reference[1], 0.5 * reference[0]])

    metrics = evaluate_recovery(reference, estimate)

    assert metrics.mean_absolute_correlation == pytest.approx(1.0)
    assert all(item.si_sdr_db == float("inf") for item in metrics.per_source)


def test_si_sdr_and_correlation_handle_poor_and_degenerate_estimates() -> None:
    reference = np.array([1.0, -1.0, 1.0, -1.0])
    assert si_sdr(reference, np.zeros_like(reference)) == float("-inf")
    assert si_sdr(reference, reference + np.array([0.1, 0.2, -0.1, 0.0])) < 30
    correlation = source_correlation(np.vstack([reference, np.ones(4)]), np.vstack([reference, np.ones(4)]))
    assert correlation[0, 0] == pytest.approx(1.0)
    assert correlation[1, 1] == 0.0


def test_metrics_reject_invalid_shapes_and_zero_reference() -> None:
    with pytest.raises(ValueError):
        evaluate_recovery(np.ones((2, 3)), np.ones((2, 4)))
    with pytest.raises(ValueError):
        si_sdr(np.zeros(3), np.ones(3))
