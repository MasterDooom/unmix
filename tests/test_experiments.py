import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from run_synthetic_experiments import run_experiment


def test_synthetic_experiment_writes_reproducible_artifacts(tmp_path) -> None:
    rows = run_experiment(tmp_path, n_samples=3000)

    assert len(rows) == 4
    assert (tmp_path / "synthetic_metrics.json").is_file()
    assert (tmp_path / "synthetic_experiment_metadata.json").is_file()
    assert (tmp_path / "plots" / "synthetic_quality_vs_noise.png").is_file()
    assert all(0.0 <= row["ica_mean_absolute_correlation"] <= 1.0 for row in rows)
    assert rows[0]["ica_mean_absolute_correlation"] > 0.98
    assert rows[0]["ica_mean_absolute_correlation"] > rows[0]["pca_mean_absolute_correlation"]
