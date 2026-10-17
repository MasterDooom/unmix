# Unmix web workspace

`backend/` is a thin FastAPI API. `frontend/` is a React, TypeScript, Vite, and
Tailwind interface. Neither changes the numerical API in `src/unmix/`.

## Start locally

From the repository root, use the commands in the root [README](../README.md).
The API is at `http://localhost:8000`; the Vite workspace is normally at
`http://localhost:5173`.

## Hosted API configuration

The frontend supports separate API origins so heavy pretrained inference does not have to run on the small Mix Lab API:

- `UNMIX_API_BASE`: the main FastAPI service used for Mix Lab.
- `UNMIX_TRACK_API_BASE`: optional, separate Track Lab inference service. Set this as a GitHub Actions repository variable; the Pages build passes it to Vite as `VITE_TRACK_API_BASE`. It must implement `GET /api/health`, `POST /api/track-lab/separate` with multipart field `track`, and serve returned `/media/...` URLs from the same origin.

If `UNMIX_TRACK_API_BASE` is unset, the frontend falls back to the main API. It does not bypass the main host's model/resource limits, and Track Lab is disabled in the UI when the configured endpoint reports it is unavailable. A configured URL alone is not proof of successful inference; verify health, CORS, a real separation request, and stem downloads on the deployed service.

## Workflows and safety boundaries

**Mix Lab** accepts a variable number of source files and JSON mixing matrix
`A` with shape `(n_mixtures, n_sources)`. It rejects non-finite, rank-deficient,
or underdetermined matrices before processing. Its default matrix has 1.0 on the
diagonal and 0.35 off-diagonal, so sources are genuinely cross-mixed without
requiring the user to edit the matrix. Stereo source files are explicitly
averaged to mono before mixing; this is a convenience, not a stereo separation
algorithm, and phase-cancelled material should be converted to a good mono source
before upload. The separator receives only the resulting mixtures and expected
component count. Known files are used only for metrics after separation.

**Track Lab** uses `web/backend/app/track_lab.py`, a lazy optional adapter for
[`audio-separator`](https://github.com/nomadkaraoke/python-audio-separator).
The default Windows launcher installs `web/requirements-track-lab.txt` (unless
`-CoreOnly` is passed). The selected runtime is CPU-only PyTorch plus
`audio-separator[cpu]` and the required `audioread` dependency. Track Lab
defaults to `UVR-MDX-NET-Inst_HQ_5.onnx`, a lighter ONNX vocal/instrumental
preset selected for more responsive CPU operation than the ~1 GB RoFormer
checkpoint tested during development. We explicitly install CPU-only PyTorch
wheels before the model package to avoid downloading the CUDA stack on ordinary
machines. The model is downloaded on first use and cached in the user's
`~/.cache/unmix/audio-separator-models` directory (overridable with
`AUDIO_SEPARATOR_MODEL_DIR`), outside temporary per-job output folders. One
model instance is reused and inference is serialized. The UI labels results as
estimates; the selected preset does not separate drums, bass, and instruments
into individual stems.

Audio Separator is MIT licensed. Its project asks users of its default or
Ultimate Vocal Remover-derived models to credit the relevant UVR developers; see
its model documentation before distributing outputs. The adapter itself contains
no copied model code. It may need FFmpeg depending on the upload format and
installed model runtime. A real Track Lab run is therefore an opt-in integration
task, not evidence supplied by the mocked API tests.

The API allows WAV, FLAC, MP3, M4A, and OGG filename extensions, streams each
upload to a per-job directory with a 100 MB cap, and rejects decodable audio
longer than 20 minutes. Actual decoder support depends on the installed
SoundFile/libsndfile and optional model tooling. Successful jobs remain available
for download for one hour and are removed during future requests; do not use this
local server as archival storage. There is no account, database, or cloud upload
service.

## Tests

```powershell
$env:PYTHONPATH = "web\backend;src"
python -m pytest -q web/backend/tests
Set-Location web\frontend
npm run test
npm run build
```

The regular CI API tests include an actual Mix Lab upload-to-FastICA-to-download
round trip, using generated WAV sources. The separate
`.github/workflows/track-lab-smoke.yml` job installs FFmpeg and the real CPU model
runtime, generates a short synthetic stereo fixture, uploads it through FastAPI,
runs pretrained inference, and verifies the returned audio downloads. This is an
infrastructure/model smoke test, not a quality benchmark on real music; run it
from GitHub Actions to verify model loading and output compatibility after
changing the model adapter or dependencies.
