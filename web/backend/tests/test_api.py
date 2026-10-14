"""Workflow tests that mock only heavyweight audio/model processing."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import main


def _skip_duration_check(monkeypatch) -> None:
    monkeypatch.setattr(main, "_validate_duration", lambda path: None)


def test_health_reports_optional_track_lab() -> None:
    with TestClient(main.app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "track_lab_optional": True}


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
