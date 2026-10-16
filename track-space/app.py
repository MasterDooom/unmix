from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

ROOT = Path("/data")
JOBS = ROOT / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)
MAX_BYTES = 100 * 1024 * 1024
ALLOWED = {".wav", ".flac", ".mp3", ".m4a", ".ogg"}
MODEL = "UVR-MDX-NET-Inst_HQ_5.onnx"
separator = None
separator_lock = Lock()

app = FastAPI(title="Unmix Track Lab API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://masterdooom.github.io",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.mount("/media", StaticFiles(directory=JOBS), name="media")


@app.get("/api/health")
def health():
    return {"status": "ok", "api_contract_version": 1, "track_lab_enabled": True}


@app.post("/api/track-lab/separate")
async def separate(track: UploadFile = File(...)):
    global separator
    suffix = Path(track.filename or "").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(415, "Use WAV, FLAC, MP3, M4A, or OGG.")
    job = JOBS / uuid.uuid4().hex
    job.mkdir()
    source = job / f"input{suffix}"
    size = 0
    try:
        with source.open("wb") as out:
            while chunk := await track.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(413, "Maximum upload size is 100 MB.")
                out.write(chunk)
        if size == 0:
            raise HTTPException(400, "The uploaded file is empty.")

        import soundfile as sf
        try:
            info = sf.info(source)
            duration = info.frames / info.samplerate
        except Exception:
            # Audio Separator/FFmpeg can decode formats libsndfile cannot inspect.
            import subprocess
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(source)],
                capture_output=True, text=True, check=True, timeout=20,
            )
            duration = float(probe.stdout.strip())
        if not 0 < duration <= 1200:
            raise HTTPException(413, "Audio duration must be 20 minutes or less.")

        output = job / "stems"
        output.mkdir()
        with separator_lock:
            if separator is None:
                from audio_separator.separator import Separator
                separator = Separator(
                    output_dir=str(output),
                    model_file_dir=os.environ.get("AUDIO_SEPARATOR_MODEL_DIR", "/data/models"),
                    output_format="WAV",
                    use_soundfile=True,
                )
                separator.load_model(model_filename=MODEL)
            else:
                separator.output_dir = str(output)
            reported = separator.separate(str(source))

        paths = []
        for item in reported or []:
            candidate = (output / Path(item).name).resolve()
            if candidate.is_file() and candidate.stat().st_size > 44:
                paths.append(candidate)
        paths = list(dict.fromkeys(paths))
        if len(paths) < 2:
            paths = [p for p in output.glob("*.wav") if p.stat().st_size > 44]
        if len(paths) < 2:
            raise RuntimeError("The model did not produce two valid WAV stems.")

        stems = []
        for path in paths:
            name = path.stem
            if "(Vocals)" in name or "vocal" in name.lower():
                label = "Vocals"
            elif "(Instrumental)" in name or "instrumental" in name.lower():
                label = "Instrumental"
            else:
                label = name.replace("_", " ")
            stems.append({"name": label, "url": f"/media/{job.name}/stems/{path.name}"})
        return {"preset": MODEL, "stems": stems}
    except HTTPException:
        shutil.rmtree(job, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(job, ignore_errors=True)
        raise HTTPException(500, f"Separation failed: {type(exc).__name__}: {exc}") from exc
