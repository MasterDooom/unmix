"""Run a small deterministic synthetic mixing experiment.

From the repository root:
    python experiments/run_mixing_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from unmix.mixing import mix_sources  # noqa: E402


def make_sources(n_samples: int = 4000) -> np.ndarray:
    """Create three independent, non-Gaussian toy sources for a smoke test."""
    rng = np.random.default_rng(42)
    t = np.linspace(0.0, 8.0, n_samples, endpoint=False)

    # Different distributions make this a useful deterministic input fixture.
    speech_like = np.tanh(2.5 * np.sin(2 * np.pi * 0.7 * t))
    music_like = np.sign(np.sin(2 * np.pi * 1.3 * t))
    ambient_like = rng.laplace(loc=0.0, scale=0.35, size=n_samples)

    sources = np.vstack([speech_like, music_like, ambient_like])
    sources -= sources.mean(axis=1, keepdims=True)
    sources /= sources.std(axis=1, keepdims=True)
    return sources


def main() -> None:
    sources = make_sources()
    mixing_matrix = np.array(
        [
            [1.0, 0.5, 0.2],
            [0.3, 1.0, 0.4],
            [0.6, 0.2, 1.0],
        ],
        dtype=np.float64,
    )
    mixtures = mix_sources(sources, mixing_matrix)

    print(f"Sources:  {sources.shape}")
    print(f"Mixtures: {mixtures.shape}")
    print("Mixing matrix:")
    print(mixing_matrix)
    print("Mixture standard deviations:", np.round(mixtures.std(axis=1), 3))
    print("Stage 1 passed: synthetic sources were mixed successfully.")


if __name__ == "__main__":
    main()
