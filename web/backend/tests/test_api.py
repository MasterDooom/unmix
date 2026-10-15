"""Workflow tests that mock only heavyweight audio/model processing."""

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import soundfile as sf

from fastapi.testclient import TestClient

from app import main


def _skip_duration_check(monkeypatch) -> None:
    monkeypatch.setattr(main, "_validate_duration", lambda path: None)


def test_health_reports_optional_track_lab() -> None:
    with TestClient(main.app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["track_lab_optional"] is True
    assert isinstance(body["track_lab_dependencies_installed"], bool)
    assert isinstance(body["ffmpeg_available"], bool)




def test_default_mixing_matrix_is_nontrivial_and_full_rank() -> None:
    matrix = main._matrix(None, 3)
    assert matrix.shape == (3, 3)
    np.testing.assert_allclose(np.diag(matrix), np.ones(3))
    np.testing.assert_allclose(matrix[matrix != 1.0], np.full(6, 0.35))
    assert np.linalg.matrix_rank(matrix) == 3


def test_track_lab_invalid_file_returns_client_error_not_internal_server_error(monkeypatch) -> None:
    with TestClient(main.app) as client:
        response = client.post(
            "/api/track-lab/separate",
            files={"track": ("song.exe", b"not audio", "application/octet-stream")},
        )
    assert response.status_code == 415
    assert "Unsupported audio format" in response.json()["detail"]


def test_mix_lab_rejects_rank_deficient_matrix(monkeypatch) -> None:
    _skip_duration_check(monkeypatch)
    with TestClient(main.app) as client:
        response = client.post(
            "/api/mix-lab/separate",
            data={"mixing_matrix": "[[1, 1], [2, 2]]"},
            files=[
                ("sources", ("first.wav", b"x", "audio/wav")),
                ("sources", ("second.wav", b"y", "audio/wav")),
            ],
        )
    assert response.status_code == 400
    assert "full column rank" in response.json()["detail"]


def test_mix_lab_runs_pipeline_and_returns_media_urls(monkeypatch) -> None:
    def fake_run(paths: list[Path], matrix, output: Path) -> dict[str, object]:
        assert len(paths) == 2
        assert matrix.shape == (2, 2)
        return {
            "sample_rate": 8_000,
            "converged": True,
            "iterations": 7,
            "mixture_url": "/media/mix-test/mixtures.wav",
            "stems": [{"name": "component_1", "url": "/media/mix-test/component_1.wav"}],
            "metrics": {"mean_absolute_correlation": 0.99, "mean_si_sdr_db": 24.0, "per_source": []},
        }

    monkeypatch.setattr(main, "_run_mix", fake_run)
    _skip_duration_check(monkeypatch)
    with TestClient(main.app) as client:
        response = client.post(
            "/api/mix-lab/separate",
            files=[
                ("sources", ("first.wav", b"data", "audio/wav")),
                ("sources", ("second.wav", b"data", "audio/wav")),
            ],
        )
    assert response.status_code == 200
    assert response.json()["metrics"]["mean_absolute_correlation"] == 0.99


def test_track_lab_surfaces_optional_backend_error(monkeypatch) -> None:
    def unavailable(source: Path, output: Path) -> list[Path]:
        raise main.TrackLabUnavailable("install the optional backend")

    monkeypatch.setattr(main, "separate_track", unavailable)
    _skip_duration_check(monkeypatch)
    with TestClient(main.app) as client:
        response = client.post(
            "/api/track-lab/separate",
            files={"track": ("song.wav", b"data", "audio/wav")},
        )
    assert response.status_code == 503
    assert "optional backend" in response.json()["detail"]

def test_duration_validation_uses_ffprobe_for_unsupported_formats(monkeypatch, tmp_path) -> None:
    path = tmp_path / "song.m4a"
    path.write_bytes(b"test content")
    monkeypatch.setattr(main.shutil, "which", lambda name: "ffprobe" if name == "ffprobe" else None)
    monkeypatch.setattr(
        main.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="12.5\n"),
    )
    main._validate_duration(path)

def _wav_bytes(samples: np.ndarray, sample_rate: int = 8_000) -> bytes:
    buffer = io.BytesIO()
    sf.write(buffer, samples, sample_rate, format="WAV", subtype="FLOAT")
    return buffer.getvalue()


def test_mix_lab_processes_real_audio_and_serves_result_files() -> None:
    rng = np.random.default_rng(91)
    samples = 8_000
    sources = np.vstack([
        rng.laplace(size=samples),
        rng.uniform(-1.0, 1.0, size=samples),
    ])
    sources = (sources - sources.mean(axis=1, keepdims=True)) / sources.std(axis=1, keepdims=True)
    matrix = "[[1.0, 0.4], [0.3, 1.2]]"

    with TestClient(main.app) as client:
        response = client.post(
            "/api/mix-lab/separate",
            data={"mixing_matrix": matrix},
            files=[
                ("sources", ("first.wav", _wav_bytes(np.column_stack([sources[0], 0.8 * sources[0]])), "audio/wav")),
                ("sources", ("second.wav", _wav_bytes(sources[1]), "audio/wav")),
            ],
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["converged"] is True
        assert len(result["stems"]) == 2
        assert result["iterations"] > 0
        mixture = client.get(result["mixture_url"])
        assert mixture.status_code == 200
        assert len(mixture.content) > 44
        for stem in result["stems"]:
            media = client.get(stem["url"])
            assert media.status_code == 200
            assert len(media.content) > 44

