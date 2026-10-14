# Unmix the Signal — ICA from Scratch

Recover independent audio sources from recordings containing mixtures of those sources. This project implements PCA whitening and Independent Component Analysis (ICA) ourselves rather than calling a ready-made ICA implementation.

## Current status

**Stages 1–5: end-to-end reproducible workflow.** The project provides validated
mixing, whitening, symmetric FastICA, ambiguity-aware recovery metrics, WAV
input/output, a command-line audio demo, and deterministic experiments.
Runtime verification requires an environment with the dependencies in
`requirements.txt`; the bundled Python 3.12 runtime verified the NumPy-only
whitening/FastICA core, while full audio/plot/test execution still needs SciPy,
SoundFile, Matplotlib, and pytest. See the report for details.

## Architecture

```text
src/unmix/
├── mixing.py          # X = A @ S, with input validation
├── preprocessing.py  # centering and full-rank PCA whitening
├── ica.py             # symmetric FastICA from scratch
├── audio.py           # mono WAV loading, resampling, and safe export
├── metrics.py         # permutation/sign/scale-aware recovery metrics
└── pipeline.py        # thin audio workflow orchestration

experiments/
├── run_mixing_demo.py
├── run_synthetic_experiments.py
└── run_audio_demo.py

tests/
├── test_mixing.py
├── test_preprocessing.py
├── test_ica.py
├── test_metrics.py
├── test_audio_pipeline.py
└── test_experiments.py
```

## Setup

Python 3.10 or newer is recommended.

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
$env:PYTHONPATH = "src"
pytest -q
python experiments/run_mixing_demo.py
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
PYTHONPATH=src pytest -q
python experiments/run_mixing_demo.py
```

## Mathematical convention

Sources are stored as a matrix `S` with shape `(n_sources, n_samples)`. A mixing matrix `A` has shape `(n_mixtures, n_sources)`. The mixed recordings are:

```text
X = A @ S
```

The separator will receive only `X`; the original `S` and known `A` are retained strictly for evaluation. Source recovery is ambiguous up to permutation and scale (and potentially sign).

## Project rules

- Do not use scikit-learn FastICA or another ready-made ICA implementation.
- Use NumPy/SciPy for general numerical primitives, including covariance and eigendecomposition.
- Build in stages and run tests at each stage.
- Use synthetic signals with known ground truth before testing real audio.
- Report only tests and experiments that were actually run.

See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for the source of truth and implementation acceptance criteria.

## Local web workspace

### One-command Windows startup

From the repository root in PowerShell, run:

```powershell
.\web\start-local.ps1
```

The launcher installs the API dependencies and CPU Track Lab model dependencies, starts FastAPI and Vite in separate terminals, waits for the API health endpoint, and opens the website. The pretrained model weights download on first separation, so the first run can take a while and needs disk space. If FFmpeg is missing, the launcher attempts to install it with WinGet; without WinGet, install FFmpeg separately and reopen the terminal. Use `-CoreOnly` to skip heavyweight Track Lab dependencies (Mix Lab/API only), or `-SkipInstall` when dependencies are already installed.

The optional website layer provides two deliberately different workflows:

- **Track Lab** sends one finished track to an *optional* pretrained model adapter.
  Its returned stems are estimates, not verified original instrument tracks. The
  core ICA package has no model dependency.
- **Mix Lab** uploads two or more known clean, mono sources, creates `X = A @ S`
  from the user-provided full-column-rank matrix, runs this repository's FastICA,
  and evaluates recovery only after separation. It supports any source count the
  matrix and audio resources can reasonably handle; it is not fixed at three.

Install the core plus web API dependencies, then start the API and Vite server in
two shells. The frontend proxies `/api` and `/media` to the local API.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r web\requirements.txt
$env:PYTHONPATH = "web\backend;src"
uvicorn app.main:app --reload --port 8000
```

```powershell
Set-Location web\frontend
npm install
npm run dev
```

Open the printed Vite address (normally `http://localhost:5173`). Run the API
workflow tests with `PYTHONPATH="web/backend;src" python -m pytest -q
web/backend/tests`, and the browser checks with `npm run test` / `npm run build`.
The Track Lab adapter is intentionally not installed by the command above:

```powershell
pip install -r web\requirements-track-lab.txt
```

That optional adapter uses Audio Separator's documented default preset. It can
download model weights on first use and depends on a suitable FFmpeg setup; run
it only after reviewing the model licence/attribution notes in `web/README.md`.
Uploads are limited to 100 MB per file and live in temporary per-job directories
under `web/runtime/`; the server removes expired jobs on later requests. Upload
only material you have rights to use.

## Mathematical API

All numerical APIs accept arrays shaped `(channels, samples)`. Use
`pca_whiten(mixtures)` to center and whiten a full-rank recording, or use
`fastica(mixtures)` for the complete center → whiten → separate path. The
separator accepts only observed mixtures and returns `FastICAResult`, including
separated rows, the unmixing transform, channel means, and convergence details.
Rows are inherently ambiguous up to permutation, sign, and scale.
For more recorded channels than expected sources, call
`fastica(mixtures, n_components=source_count)` to retain the leading PCA
subspace before ICA.

## Audio demo and experiments

The default audio demo uses three generated source WAVs, so it needs no network
download. It writes a multichannel mixture WAV and one WAV per recovered
component. You may instead give three clean mono WAV source paths. Multi-channel
inputs are rejected by default; use the API's `channel_policy="mixdown"` only
when averaging channels is appropriate. Different source sample rates are
resampled with `scipy.signal.resample_poly`, and sources are truncated to the
shortest duration by default.

```powershell
$env:PYTHONPATH = "src"
python experiments/run_synthetic_experiments.py
python experiments/run_audio_demo.py
python experiments/run_audio_demo.py source1.wav source2.wav source3.wav
```

Exported WAVs are peak-normalized to prevent clipping. This happens after ICA;
metrics are always calculated from unnormalized numerical estimates. The
synthetic experiment writes `results/synthetic_metrics.json` and
`results/synthetic_experiment_metadata.json`, plus
`results/plots/synthetic_quality_vs_noise.png`, comparing PCA-whitened rows and
ICA over fixed-seed additive-noise trials. See [REPORT.md](REPORT.md) and
[REFERENCES.md](REFERENCES.md) for methods, limits, and sources.
