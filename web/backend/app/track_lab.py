"""Optional pretrained stem estimation through Audio Separator.

The core Mix Lab and FastICA implementation never depend on this heavy runtime.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock
from typing import Any

TRACK_LAB_MODEL = "model_mel_band_roformer_ep_3005_sdr_11.4360.ckpt"

_SEPARATOR: Any | None = None
_SEPARATOR_LOCK = Lock()


class TrackLabUnavailable(RuntimeError):
    """Raised when the optional pretrained backend is not installed."""


def separate_track(input_path: Path, output_directory: Path) -> list[Path]:
    """Run Audio Separator's documented two-stem Mel-Band RoFormer model.

    Model weights are cached outside temporary job directories, and the loaded
    model is reused for subsequent jobs. Inference is serialized because a
    single PyTorch model instance should not be mutated by concurrent requests.
    """
    global _SEPARATOR

    try:
        from audio_separator.separator import Separator
    except ImportError as error:
        raise TrackLabUnavailable(
            "Track Lab's model runtime is missing. Run web/start-local.ps1 without "
            "-CoreOnly, or install web/requirements-track-lab.txt in the active Python environment."
        ) from error

    output_directory = output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    configured_cache = os.environ.get("AUDIO_SEPARATOR_MODEL_DIR")
    model_cache = (
        Path(configured_cache).expanduser()
        if configured_cache
        else Path.home() / ".cache" / "unmix" / "audio-separator-models"
    )
    model_cache = model_cache.resolve()
    model_cache.mkdir(parents=True, exist_ok=True)

    with _SEPARATOR_LOCK:
        if _SEPARATOR is None:
            separator = Separator(
                output_dir=str(output_directory),
                model_file_dir=str(model_cache),
                output_format="WAV",
                use_soundfile=True,
            )
            separator.load_model(model_filename=TRACK_LAB_MODEL)
            _SEPARATOR = separator
        else:
            # Audio Separator documents the same instance as reusable for
            # consecutive inputs; update the per-job output destination only.
            _SEPARATOR.output_dir = str(output_directory)

        reported_outputs = _SEPARATOR.separate(str(input_path))

    # Audio Separator versions may report an absolute path or a filename. Resolve
    # either form against the explicit job output directory and verify real files.
    stems: list[Path] = []
    for reported in reported_outputs or []:
        candidate = Path(reported)
        if not candidate.is_absolute():
            candidate = output_directory / candidate.name
        candidate = candidate.resolve()
        if not candidate.is_file() or candidate.stat().st_size <= 44:
            candidate = (output_directory / Path(reported).name).resolve()
        if candidate.is_file() and candidate.stat().st_size > 44:
            stems.append(candidate)

    stems = list(dict.fromkeys(stems))
    if len(stems) < 2:
        produced = sorted(path for path in output_directory.glob("*.wav") if path.stat().st_size > 44)
        stems = list(dict.fromkeys(produced))
    if len(stems) < 2:
        raise RuntimeError(
            "Audio Separator completed without producing two readable WAV stems. "
            "Check the model, FFmpeg, and FastAPI terminal logs."
        )
    return stems
