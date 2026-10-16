"""Focused safety tests for the optional Track Lab adapter."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest

from app import track_lab


def test_separator_outputs_outside_job_directory_are_rejected(monkeypatch, tmp_path) -> None:
    outside = tmp_path / "another-job"
    outside.mkdir()
    for name in ("vocals.wav", "instrumental.wav"):
        (outside / name).write_bytes(b"RIFF" + b"\x00" * 80)

    class FakeSeparator:
        def __init__(self, *, output_dir, **kwargs) -> None:
            self.output_dir = output_dir

        def load_model(self, *, model_filename) -> None:
            assert model_filename == track_lab.TRACK_LAB_MODEL

        def separate(self, input_path: str) -> list[str]:
            return [str(outside / "vocals.wav"), str(outside / "instrumental.wav")]

    package = ModuleType("audio_separator")
    package.__path__ = []
    module = ModuleType("audio_separator.separator")
    module.Separator = FakeSeparator
    monkeypatch.setitem(sys.modules, "audio_separator", package)
    monkeypatch.setitem(sys.modules, "audio_separator.separator", module)
    monkeypatch.setattr(track_lab, "_SEPARATOR", None)
    monkeypatch.setenv("AUDIO_SEPARATOR_MODEL_DIR", str(tmp_path / "model-cache"))

    job_output = tmp_path / "current-job" / "separated"
    with pytest.raises(RuntimeError, match="without producing two readable WAV stems"):
        track_lab.separate_track(tmp_path / "input.wav", job_output)

    assert list(job_output.glob("*.wav")) == []
