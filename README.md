# Unmix the Signal — ICA from Scratch

Recover independent audio sources from recordings containing mixtures of those sources. This project implements PCA whitening and Independent Component Analysis (ICA) ourselves rather than calling a ready-made ICA implementation.

## Current status

**Stage 1: repository foundation and synthetic mixing.** The first implementation provides validated linear mixing, a deterministic synthetic demo, and unit tests. Whitening, ICA, real-audio handling, metrics, and plots will be added in later verified stages.

## Architecture

```text
src/unmix/
├── mixing.py          # X = A @ S, with input validation
├── preprocessing.py  # centering and PCA whitening (planned)
├── ica.py             # FastICA from scratch (planned)
├── audio.py           # audio loading and WAV export (planned)
├── metrics.py         # recovery metrics (planned)
└── pipeline.py        # orchestration (planned)

experiments/
└── run_mixing_demo.py

tests/
└── test_mixing.py
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
