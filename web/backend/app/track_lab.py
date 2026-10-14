"""Optional Track Lab adapter; heavy pretrained inference is never a core dependency."""

from __future__ import annotations

from pathlib import Path

TRACK_LAB_MODEL = "model_mel_band_roformer_ep_3005_sdr_11.4360.ckpt"


class TrackLabUnavailable(RuntimeError):
    """Raised when the optional pretrained backend is not installed."""


def separate_track(input_path: Path, output_directory: Path) -> list[Path]:
    """Run Audio Separator's documented default two-stem preset when installed.

    The named Mel-Band RoFormer checkpoint keeps this initial preset explicit.
    Model weights may download on first run, so this function is deliberately
    imported only by the Track Lab route and must be exercised in an opt-in
    integration environment.
    """
    try:
        from audio_separator.separator import Separator
    except ImportError as error:
        raise TrackLabUnavailable(
            "Track Lab is optional. Install web/requirements-track-lab.txt and "
            "configure FFmpeg/model storage before running pretrained separation."
        ) from error
    output_directory.mkdir(parents=True, exist_ok=True)
    separator = Separator(output_dir=str(output_directory))
    separator.load_model(model_filename=TRACK_LAB_MODEL)
    return [output_directory / Path(name).name for name in separator.separate(str(input_path))]
