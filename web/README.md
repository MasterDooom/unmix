# Unmix web workspace

`backend/` is a thin FastAPI API. `frontend/` is a React, TypeScript, Vite, and
Tailwind interface. Neither changes the numerical API in `src/unmix/`.

## Start locally

From the repository root, use the commands in the root [README](../README.md).
The API is at `http://localhost:8000`; the Vite workspace is normally at
`http://localhost:5173`.

## Workflows and safety boundaries

**Mix Lab** accepts a variable number of source files and JSON mixing matrix
`A` with shape `(n_mixtures, n_sources)`. It rejects non-finite, rank-deficient,
or underdetermined matrices before processing. It loads sources, creates `A @ S`,
then gives only observed mixtures plus the expected component count to FastICA.
Known files are used only after that point for recovery metrics. Files are
currently processed as mono because the established audio pipeline intentionally
rejects multichannel source material by default.

**Track Lab** uses `web/backend/app/track_lab.py`, a lazy optional adapter for
[`audio-separator`](https://github.com/nomadkaraoke/python-audio-separator).
Install `web/requirements-track-lab.txt` separately. Its default model and any
first-run model-weight download are not exercised by ordinary tests. Audio
Separator documents support for several model families; this application exposes
one explicit `model_mel_band_roformer_ep_3005_sdr_11.4360.ckpt` preset first
rather than promising arbitrary instruments or model choices. The user interface
labels its outputs as estimates.

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

The API tests mock the heavyweight pretrained model and the audio pipeline where
needed; they test upload validation, matrix rejection, response format, and the
optional-backend failure state. The real model must be tested separately after
the optional installation is complete.
