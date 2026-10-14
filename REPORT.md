# Unmix the Signal: ICA-Based Source Separation

## Problem and assumptions

The project observes linear instantaneous mixtures `X = A @ S` and estimates
independent source rows `S`. ICA assumes full-rank mixing, enough observed
channels, statistically independent non-Gaussian sources, and sufficient
samples. It cannot in general separate arbitrary correlated sources, nonlinear
mixes, or underdetermined recordings.

## Method

Each mixture channel is centered. With `C = Xc Xc^T / N`, eigendecomposition
`C = E D E^T` gives the whitening transform `D^(-1/2) E^T`. Whitening makes
the covariance identity but only decorrelates the data; it does not establish
statistical independence.

The separator then uses symmetric FastICA with `g(u)=tanh(u)`:

`W <- E[g(WZ) Z^T] / N - diag(E[g'(WZ)]) W`

After each update it symmetrically decorrelates rows of `W`. Convergence uses
sign-invariant alignment between successive unmixing rows. The implementation
rejects rank-deficient covariance and reports non-convergence explicitly.

## Evaluation

Recovered rows may be permuted, sign-flipped, and scaled. Evaluation therefore
uses a linear-sum assignment maximizing absolute Pearson correlation. It also
reports SI-SDR in dB by projecting an estimate onto its reference and comparing
target and residual energy. Correlation measures association; SI-SDR measures
projection error energy. SI-SDR is undefined for a zero-energy reference;
this implementation rejects it, returns `-inf` for a zero estimate, and `inf`
for an exact scaled reference.

## Experiments and audio workflow

`run_synthetic_experiments.py` uses fixed seeds, non-Gaussian sources, a fixed
full-rank matrix, and controlled additive noise. It compares PCA-whitened rows
against FastICA and writes JSON metrics plus a plot. `run_audio_demo.py`
generates deterministic WAV sources without downloading data, or accepts three
user-supplied clean mono WAVs. Sources are resampled using polyphase FIR
resampling and truncated to the shortest duration by default. Exports are peak
normalized only at write time; evaluation uses unnormalized estimates.

## Results and verification status

A bundled Python 3.12.14 runtime with NumPy 2.3.5 verified the numerical core.
For three independent, non-Gaussian sources with 8,000 samples, fixed seed 91,
and two full-rank 3×3 mixing matrices, FastICA converged in 6 and 4 iterations;
the minimum best-match absolute correlations were 0.9999001 and 0.9999001.
On a separate 3-channel whitening check with 6,000 samples, the maximum
covariance error from identity was `8.88e-16`; repeated FastICA runs with the
same seed produced identical output. A rank-deficient input raised the expected
`ValueError`.

An overdetermined 3-channel/2-source synthetic mixture was also verified with
`n_components=2`: it converged in 3 iterations, returned a 2×3 unmixing matrix,
and achieved a minimum best-match absolute correlation of `0.9999455`.

Full pytest, audio, plot, and metric execution remains blocked: the system
Python 3.14 lacks NumPy, and the bundled Python lacks SciPy, SoundFile,
Matplotlib, and pytest. An earlier package installation attempt was blocked by
TLS certificate validation and was not retried. Consequently no WAV, JSON, or
plot artifacts are reported as measured; the scripts generate genuine metrics
and artifacts only when run in an environment satisfying `requirements.txt`.

## Limitations

Finite samples, additive noise, near-singular matrices, nonstationary audio,
and weak non-Gaussianity can impair recovery. Audio is normalized independently
only for playable export, so output loudness is not a measure of separation
quality. Synthetic sources demonstrate algorithm mechanics, not real-world
speech/music separation performance.
