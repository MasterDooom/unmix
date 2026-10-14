"""FastAPI entry point for the local Track Lab and Mix Lab workflows."""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
import time
import uuid
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from unmix.pipeline import run_audio_separation

from .track_lab import TRACK_LAB_MODEL, TrackLabUnavailable, separate_track

RUNTIME = ROOT / "web" / "runtime"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_DURATION_SECONDS = 20 * 60
JOB_TTL_SECONDS = 60 * 60
ALLOWED_SUFFIXES = {".wav", ".flac", ".mp3", ".m4a", ".ogg"}
app = FastAPI(title="Unmix API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
RUNTIME.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=RUNTIME), name="media")


def _cleanup_expired_jobs() -> None:
    cutoff = time.time() - JOB_TTL_SECONDS
    for candidate in RUNTIME.iterdir():
        if candidate.is_dir() and candidate.stat().st_mtime < cutoff:
            shutil.rmtree(candidate, ignore_errors=True)


async def _save_upload(upload: UploadFile, directory: Path) -> Path:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(415, f"Unsupported audio format: {suffix or 'unknown'}")
    target = directory / f"source-{uuid.uuid4().hex}{suffix}"
    size = 0
    with target.open("wb") as stream:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                target.unlink(missing_ok=True)
                raise HTTPException(413, "Audio upload exceeds the 100 MB limit.")
            stream.write(chunk)
    if size == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(400, "Audio upload is empty.")
    return target


def _validate_duration(path: Path) -> None:
    """Reject files whose decoded duration is unsafe for the local service."""
    try:
        import soundfile as sf

        metadata = sf.info(path)
        duration = metadata.frames / metadata.samplerate
    except (RuntimeError, ZeroDivisionError) as error:
        raise ValueError(f"Could not inspect audio file {path.name}: {error}") from error
    if not np.isfinite(duration) or duration <= 0 or duration > MAX_DURATION_SECONDS:
        raise ValueError(f"Audio duration must be between 0 and {MAX_DURATION_SECONDS // 60} minutes.")


def _matrix(text: str | None, source_count: int) -> np.ndarray:
    if not text:
        return np.eye(source_count, dtype=np.float64)
    try:
        matrix = np.asarray(json.loads(text), dtype=np.float64)
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise HTTPException(400, "mixing_matrix must be a JSON numeric matrix.") from error
    if matrix.ndim != 2 or matrix.shape[1] != source_count:
        raise HTTPException(400, "Matrix columns must equal the number of uploaded sources.")
    if matrix.shape[0] < source_count:
        raise HTTPException(400, "ICA needs at least as many mixture rows as source columns.")
    if not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix) < source_count:
        raise HTTPException(400, "The mixing matrix must be finite and have full column rank.")
    return matrix


def _run_mix(paths: list[Path], matrix: np.ndarray, output: Path) -> dict[str, object]:
    run = run_audio_separation(paths, matrix, output, random_state=17, tol=1e-7)
    relative = lambda path: f"/media/{path.relative_to(RUNTIME).as_posix()}"
    return {
        "sample_rate": run.sample_rate,
        "converged": run.ica.converged,
        "iterations": run.ica.n_iter,
        "mixture_url": relative(run.mixture_path),
        "stems": [{"name": path.stem, "url": relative(path)} for path in run.component_paths],
        "metrics": {
            "mean_absolute_correlation": run.metrics.mean_absolute_correlation,
            "mean_si_sdr_db": run.metrics.mean_si_sdr_db,
            "per_source": [item.__dict__ for item in run.metrics.per_source],
        },
    }


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"status": "ok", "track_lab_optional": True}


@app.post("/api/mix-lab/separate")
async def mix_lab(
    sources: list[UploadFile] = File(...), mixing_matrix: str | None = Form(default=None)
) -> dict[str, object]:
    if len(sources) < 2:
        raise HTTPException(400, "Mix Lab requires at least two clean source files.")
    _cleanup_expired_jobs()
    job = RUNTIME / f"mix-{uuid.uuid4().hex}"
    job.mkdir()
    try:
        paths = [await _save_upload(source, job) for source in sources]
        for path in paths:
            _validate_duration(path)
        matrix = _matrix(mixing_matrix, len(paths))
        return await asyncio.wait_for(asyncio.to_thread(_run_mix, paths, matrix, job), timeout=120)
    except HTTPException:
        shutil.rmtree(job, ignore_errors=True)
        raise
    except asyncio.TimeoutError as error:
        shutil.rmtree(job, ignore_errors=True)
        raise HTTPException(504, "Mix Lab exceeded its 120-second processing limit.") from error
    except (ValueError, FloatingPointError, RuntimeError) as error:
        shutil.rmtree(job, ignore_errors=True)
        raise HTTPException(422, str(error)) from error


@app.post("/api/track-lab/separate")
async def track_lab(track: UploadFile = File(...)) -> dict[str, object]:
    _cleanup_expired_jobs()
    job = RUNTIME / f"track-{uuid.uuid4().hex}"
    job.mkdir()
    try:
        source = await _save_upload(track, job)
        _validate_duration(source)
        stems = await asyncio.wait_for(asyncio.to_thread(separate_track, source, job / "separated"), timeout=600)
        return {
            "preset": TRACK_LAB_MODEL,
            "stems": [{"name": stem.stem, "url": f"/media/{stem.relative_to(RUNTIME).as_posix()}"} for stem in stems],
        }
    except TrackLabUnavailable as error:
        shutil.rmtree(job, ignore_errors=True)
        raise HTTPException(503, str(error)) from error
    except asyncio.TimeoutError as error:
        shutil.rmtree(job, ignore_errors=True)
        raise HTTPException(504, "Track Lab exceeded its 10-minute processing limit.") from error
    except (ValueError, RuntimeError) as error:
        shutil.rmtree(job, ignore_errors=True)
        raise HTTPException(422, str(error)) from error
