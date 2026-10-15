"""End-to-end smoke test for the real pretrained Track Lab model.

Uses deterministic generated audio to exercise dependency loading, model download,
inference, FastAPI upload/response handling, and the media download endpoint.
It intentionally does not treat synthetic input as evidence of real-song quality.
"""
from __future__ import annotations

import io
import json
import time

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from app.main import app


def make_fixture(duration_seconds: int = 8, sample_rate: int = 44_100) -> bytes:
    samples = duration_seconds * sample_rate
    time_axis = np.arange(samples, dtype=np.float32) / sample_rate

    # Two deterministic, spectrally different signals make a valid non-silent
    # stereo music-like fixture without downloading or redistributing audio.
    vocal_like = (
        0.22
        * np.sin(2 * np.pi * 190 * time_axis)
        * (0.55 + 0.45 * np.sin(2 * np.pi * 3.1 * time_axis))
    )
    instrumental_like = (
        0.16 * np.sin(2 * np.pi * 110 * time_axis)
        + 0.08 * np.sin(2 * np.pi * 330 * time_axis)
        + 0.04 * np.sin(2 * np.pi * 880 * time_axis)
    )
    beat_phase = np.mod(time_axis, 0.5)
    beat = 0.12 * np.exp(-beat_phase * 24) * np.sin(2 * np.pi * 1400 * time_axis)
    mono = vocal_like + instrumental_like + beat
    stereo = np.column_stack([mono, 0.96 * mono + 0.015 * np.sin(2 * np.pi * 440 * time_axis)])
    stereo *= 0.75 / np.max(np.abs(stereo))

    output = io.BytesIO()
    sf.write(output, stereo, sample_rate, format="WAV", subtype="PCM_16")
    return output.getvalue()


def main() -> None:
    start = time.monotonic()
    fixture = make_fixture()
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200, health.text
        health_data = health.json()
        assert health_data["track_lab_dependencies_installed"] is True, health_data
        assert health_data["ffmpeg_available"] is True, health_data

        response = client.post(
            "/api/track-lab/separate",
            files={"track": ("track-lab-smoke.wav", fixture, "audio/wav")},
        )
        assert response.status_code == 200, (
            f"Track Lab returned HTTP {response.status_code}: {response.text}"
        )
        result = response.json()
        assert result["preset"], result
        stems = result["stems"]
        assert len(stems) == 2, result
        assert {stem["name"] for stem in stems} == {"Vocals", "Instrumental"}, result

        verified = []
        for stem in stems:
            media = client.get(stem["url"])
            assert media.status_code == 200, (
                f"Media URL {stem['url']} returned HTTP {media.status_code}"
            )
            assert len(media.content) > 44, f"Empty audio output for {stem['name']}"
            assert media.content[:4] == b"RIFF" and media.content[8:12] == b"WAVE", (
                f"Stem {stem['name']} is not a WAV file"
            )
            decoded, rate = sf.read(io.BytesIO(media.content), dtype="float32")
            assert rate > 0 and decoded.size > 0 and np.isfinite(decoded).all(), stem
            verified.append({
                "name": stem["name"],
                "sample_rate": rate,
                "sample_count": int(decoded.shape[0]),
                "download_bytes": len(media.content),
            })

    print(json.dumps({
        "status": "passed",
        "workflow": "real pretrained Track Lab API smoke test",
        "model": result["preset"],
        "input_duration_seconds": 8,
        "outputs": verified,
        "elapsed_seconds": round(time.monotonic() - start, 2),
        "note": "Synthetic-fixture smoke test only; not an audio-quality benchmark.",
    }, indent=2))


if __name__ == "__main__":
    main()
