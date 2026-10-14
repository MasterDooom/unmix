"""Thin orchestration for mixing, ICA separation, export, and evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from .audio import load_sources, write_audio, write_components
from .ica import FastICAResult, fastica
from .metrics import RecoveryMetrics, evaluate_recovery
from .mixing import mix_sources


@dataclass(frozen=True)
class AudioSeparationRun:
    """Output metadata; metrics use ground truth only after separation."""

    mixture_path: Path
    component_paths: tuple[Path, ...]
    sample_rate: int
    ica: FastICAResult
    metrics: RecoveryMetrics


def separate_mixtures(mixtures: np.ndarray, **ica_options: object) -> FastICAResult:
    """Separate observed mixtures only; source references are never accepted."""
    return fastica(mixtures, **ica_options)


def run_audio_separation(
    source_paths: Sequence[str | Path],
    mixing_matrix: np.ndarray,
    output_directory: str | Path,
    *,
    sample_rate: int | None = None,
    channel_policy: str = "reject",
    duration_policy: str = "truncate",
    **ica_options: object,
) -> AudioSeparationRun:
    """Load known clean sources, create mixtures, separate observations, and export WAVs."""
    sources, resolved_rate = load_sources(
        source_paths,
        sample_rate=sample_rate,
        channel_policy=channel_policy,  # type: ignore[arg-type]
        duration_policy=duration_policy,  # type: ignore[arg-type]
    )
    mixtures = mix_sources(sources, mixing_matrix)
    # The source paths establish the expected component count for this known
    # mixing experiment; only mixtures and that count reach the separator.
    separator_options = {"n_components": sources.shape[0], **ica_options}
    result = separate_mixtures(mixtures, **separator_options)
    output_directory = Path(output_directory)
    mixture_path = write_audio(output_directory / "mixtures.wav", mixtures, resolved_rate)
    component_paths = write_components(output_directory / "separated", result.sources, resolved_rate)
    return AudioSeparationRun(
        mixture_path=mixture_path,
        component_paths=component_paths,
        sample_rate=resolved_rate,
        ica=result,
        metrics=evaluate_recovery(sources, result.sources),
    )
