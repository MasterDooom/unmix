# Project Context — Unmix the Signal (ICA)

## Goal
Recover independent audio sources from recordings that contain linear mixtures of those sources. Implement Independent Component Analysis (ICA), including PCA whitening, from scratch. The project deliverables are reproducible code, source links, mixed and separated audio, plots, metrics, and a clear technical write-up.

## Non-negotiable constraints
- This file is the source of truth for project decisions and workflow.
- Do not use a ready-made ICA implementation (including scikit-learn FastICA). Implement the ICA algorithm ourselves.
- NumPy/SciPy may be used for general numerical operations, covariance, eigendecomposition, and signal processing.
- Keep mathematical algorithms separate from file I/O, experiments, and evaluation.
- Start with deterministic synthetic sources and known mixing matrices. Verify recovery before adding real audio.
- The ICA algorithm must receive mixtures only. Keep original sources and the mixing matrix available to evaluation code only, never as inputs to the separator.
- Preserve working systems. Make small, explicit changes, and test each stage before advancing.
- After implementation, perform a hostile review for numerical edge cases, invalid inputs, convergence, performance, maintainability, and reproducibility.

## Architecture
- `src/unmix/mixing.py`: source/mixing matrix validation and linear mixing.
- `src/unmix/preprocessing.py`: centering and PCA whitening implemented with covariance and eigendecomposition.
- `src/unmix/ica.py`: FastICA implementation from scratch.
- `src/unmix/audio.py`: audio loading, resampling, and WAV export.
- `src/unmix/metrics.py`: evaluation metrics that account for permutation and scale ambiguity.
- `src/unmix/pipeline.py`: orchestration only; no duplicated math.
- `experiments/`: reproducible experiments and comparisons.
- `tests/`: deterministic unit tests for each mathematical stage.

## Implementation stages
1. Repository foundation and synthetic source mixing.
2. Centering and PCA whitening.
3. FastICA implementation, convergence handling, and tests.
4. Real audio loading, mixing, and WAV export.
5. Evaluation metrics, plots, PCA-vs-ICA and noise experiments.
6. README/report, reproducibility checks, and hostile review.

## Initial acceptance criteria
- Sources use shape `(n_sources, n_samples)`; mixtures use shape `(n_mixtures, n_samples)`.
- Mixing is performed as `X = A @ S`, where A has shape `(n_mixtures, n_sources)`.
- Input validation catches mismatched dimensions, non-finite values, and underdetermined mixtures.
- Tests are deterministic and do not require external audio downloads.
- Never claim an experiment or test passed unless it was actually run.
