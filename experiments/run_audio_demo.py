"""Run a self-contained WAV separation demo, or provide clean mono WAV files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from unmix.audio import write_audio  # noqa: E402
from unmix.pipeline import run_audio_separation  # noqa: E402


def make_demo_sources(directory: Path, sample_rate: int = 8000) -> list[Path]:
    """Create small deterministic, generated sources; no external download is used."""
    duration = 3.0
    time = np.arange(int(sample_rate * duration)) / sample_rate
    rng = np.random.default_rng(88)
    signals = [
        0.6 * np.tanh(3 * np.sin(2 * np.pi * 220 * time)),
        0.45 * np.sign(np.sin(2 * np.pi * 330 * time)),
        0.2 * rng.laplace(size=time.size),
    ]
    paths = []
    for index, signal in enumerate(signals, start=1):
        paths.append(write_audio(directory / f"generated_source_{index}.wav", signal, sample_rate))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", type=Path, help="optional clean mono WAV source files")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "audio_demo")
    arguments = parser.parse_args()
    source_paths = arguments.sources or make_demo_sources(arguments.output / "sources")
    matrix = np.array([[1.0, 0.5, 0.2], [0.3, 1.0, 0.4], [0.6, 0.2, 1.0]])
    if len(source_paths) != matrix.shape[1]:
        raise ValueError(f"this demo matrix requires {matrix.shape[1]} source files.")
    run = run_audio_separation(source_paths, matrix, arguments.output, random_state=17, tol=1e-7)
    print(f"Mixtures: {run.mixture_path}")
    print(f"Separated components: {', '.join(map(str, run.component_paths))}")
    print(f"Sample rate: {run.sample_rate}; components: {len(run.component_paths)}")
    print(f"FastICA converged: {run.ica.converged} in {run.ica.n_iter} iterations")
    print(f"Mean matched absolute correlation: {run.metrics.mean_absolute_correlation:.4f}")


if __name__ == "__main__":
    main()
