"""Reproducible PCA-versus-ICA and additive-noise experiment."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from unmix.ica import fastica  # noqa: E402
from unmix.metrics import evaluate_recovery  # noqa: E402
from unmix.mixing import mix_sources  # noqa: E402
from unmix.preprocessing import pca_whiten  # noqa: E402


def make_sources(n_samples: int = 12000, seed: int = 2026) -> np.ndarray:
    """Create independent, non-Gaussian sources with deterministic ground truth."""
    rng = np.random.default_rng(seed)
    sources = np.vstack(
        [rng.laplace(size=n_samples), rng.uniform(-1, 1, n_samples), rng.standard_t(5, n_samples)]
    )
    return (sources - sources.mean(axis=1, keepdims=True)) / sources.std(axis=1, keepdims=True)


def run_experiment(
    output_directory: str | Path = ROOT / "results", *, n_samples: int = 12000
) -> list[dict[str, float]]:
    """Run fixed-seed recovery trials and save a JSON summary plus one plot."""
    output_directory = Path(output_directory)
    plots = output_directory / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    sources = make_sources(n_samples=n_samples)
    matrix = np.array([[1.0, 0.4, -0.2], [0.3, 1.2, 0.5], [-0.5, 0.2, 1.1]])
    clean_mixtures = mix_sources(sources, matrix)
    rng = np.random.default_rng(120)
    noise_levels = (0.0, 0.01, 0.03, 0.1)
    metadata = {
        "source_seed": 2026,
        "noise_seed": 120,
        "n_samples": n_samples,
        "mixing_matrix": matrix.tolist(),
        "noise_std_fraction_of_mixture": list(noise_levels),
        "matching_metric": "optimal absolute Pearson correlation",
    }
    rows: list[dict[str, float]] = []
    for noise_level in noise_levels:
        noise = rng.standard_normal(clean_mixtures.shape) * (noise_level * clean_mixtures.std())
        mixtures = clean_mixtures + noise
        ica_result = fastica(mixtures, random_state=17, tol=1e-7)
        ica_metrics = evaluate_recovery(sources, ica_result.sources)
        pca_metrics = evaluate_recovery(sources, pca_whiten(mixtures).whitened)
        rows.append(
            {
                "noise_std_fraction": noise_level,
                "ica_mean_absolute_correlation": ica_metrics.mean_absolute_correlation,
                "pca_mean_absolute_correlation": pca_metrics.mean_absolute_correlation,
                "ica_mean_si_sdr_db": ica_metrics.mean_si_sdr_db,
                "pca_mean_si_sdr_db": pca_metrics.mean_si_sdr_db,
            }
        )
    (output_directory / "synthetic_metrics.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (output_directory / "synthetic_experiment_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    plt.figure(figsize=(7, 4))
    plt.plot(noise_levels, [row["ica_mean_absolute_correlation"] for row in rows], marker="o", label="FastICA")
    plt.plot(noise_levels, [row["pca_mean_absolute_correlation"] for row in rows], marker="o", label="PCA whitening")
    plt.xlabel("Additive noise standard deviation / mixture standard deviation")
    plt.ylabel("Mean optimally matched absolute correlation")
    plt.ylim(0, 1.05)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(plots / "synthetic_quality_vs_noise.png", dpi=150)
    plt.close()
    return rows


if __name__ == "__main__":
    for row in run_experiment():
        print(row)
