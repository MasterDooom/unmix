"""Safe mono-audio loading, resampling, alignment, and WAV export."""

from __future__ import annotations

from dataclasses import dataclass
from math import gcd
from pathlib import Path
from typing import Literal, Sequence

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

FloatArray = np.ndarray


@dataclass(frozen=True)
class AudioBuffer:
    """Mono samples and their positive integer sample rate."""

    samples: FloatArray
    sample_rate: int


def load_audio(path: str | Path, *, channel_policy: Literal["reject", "mixdown"] = "reject") -> AudioBuffer:
    """Load one WAV source as mono float64 samples.

    Mono files are the default source convention. Multi-channel files are
    rejected unless ``channel_policy='mixdown'``, which averages channels.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"audio file does not exist: {path}")
    if channel_policy not in {"reject", "mixdown"}:
        raise ValueError("channel_policy must be 'reject' or 'mixdown'.")
    try:
        frames, sample_rate = sf.read(path, dtype="float64", always_2d=True)
    except RuntimeError as error:
        raise ValueError(f"could not read audio file {path}: {error}") from error
    if frames.shape[0] == 0 or not np.isfinite(frames).all():
        raise ValueError(f"audio file {path} is empty or contains non-finite samples.")
    if frames.shape[1] != 1 and channel_policy == "reject":
        raise ValueError(f"audio file {path} has {frames.shape[1]} channels; expected mono.")
    samples = frames[:, 0] if frames.shape[1] == 1 else frames.mean(axis=1)
    return AudioBuffer(samples=samples, sample_rate=int(sample_rate))


def resample_audio(buffer: AudioBuffer, sample_rate: int) -> AudioBuffer:
    """Resample with a polyphase FIR filter, suitable for non-periodic audio."""
    if not isinstance(sample_rate, int) or sample_rate <= 0:
        raise ValueError("sample_rate must be a positive integer.")
    if buffer.sample_rate == sample_rate:
        return buffer
    divisor = gcd(buffer.sample_rate, sample_rate)
    samples = resample_poly(buffer.samples, sample_rate // divisor, buffer.sample_rate // divisor)
    if samples.size == 0 or not np.isfinite(samples).all():
        raise FloatingPointError("resampling produced invalid audio samples.")
    return AudioBuffer(samples=np.asarray(samples, dtype=np.float64), sample_rate=sample_rate)


def load_sources(
    paths: Sequence[str | Path],
    *,
    sample_rate: int | None = None,
    channel_policy: Literal["reject", "mixdown"] = "reject",
    duration_policy: Literal["truncate", "pad"] = "truncate",
) -> tuple[FloatArray, int]:
    """Load mono source files, resample, then truncate or zero-pad durations."""
    if len(paths) == 0:
        raise ValueError("at least one source path is required.")
    buffers = [load_audio(path, channel_policy=channel_policy) for path in paths]
    target_rate = buffers[0].sample_rate if sample_rate is None else sample_rate
    buffers = [resample_audio(buffer, target_rate) for buffer in buffers]
    lengths = [buffer.samples.size for buffer in buffers]
    if duration_policy == "truncate":
        length = min(lengths)
        sources = np.vstack([buffer.samples[:length] for buffer in buffers])
    elif duration_policy == "pad":
        length = max(lengths)
        sources = np.vstack([np.pad(buffer.samples, (0, length - buffer.samples.size)) for buffer in buffers])
    else:
        raise ValueError("duration_policy must be 'truncate' or 'pad'.")
    return sources, target_rate


def write_audio(path: str | Path, samples: FloatArray, sample_rate: int, *, peak: float = 0.99) -> Path:
    """Write samples as WAV after export-only peak normalization.

    One-dimensional input is mono; two-dimensional input uses
    ``(channels, samples)`` and is transposed for SoundFile. Normalization is
    intentionally not used for evaluation or ICA.
    """
    array = np.asarray(samples, dtype=np.float64)
    if array.ndim not in {1, 2} or array.size == 0 or not np.isfinite(array).all():
        raise ValueError("samples must be a non-empty finite 1D or 2D array.")
    if not isinstance(sample_rate, int) or sample_rate <= 0 or not 0 < peak <= 1:
        raise ValueError("sample_rate must be positive and peak must be in (0, 1].")
    maximum = float(np.max(np.abs(array)))
    exported = array if maximum == 0.0 else array * (peak / maximum)
    frames = exported if exported.ndim == 1 else exported.T
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, frames, sample_rate, format="WAV", subtype="PCM_16")
    return path


def write_components(directory: str | Path, components: FloatArray, sample_rate: int, *, prefix: str = "component") -> tuple[Path, ...]:
    """Write each ICA component to a separate playable WAV file."""
    array = np.asarray(components, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError("components must have shape (components, samples).")
    directory = Path(directory)
    return tuple(write_audio(directory / f"{prefix}_{index + 1}.wav", component, sample_rate) for index, component in enumerate(array))
