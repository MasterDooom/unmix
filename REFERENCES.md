# References

- A. Hyvärinen, “Fast and Robust Fixed-Point Algorithms for Independent Component Analysis,” *IEEE Transactions on Neural Networks*, 1999. Consulted for the symmetric FastICA fixed-point approach and convergence context: <https://www.cs.helsinki.fi/u/ahyvarin/papers/fastica.shtml>.
- J. Le Roux, S. Wisdom, H. Erdogan, and J. Hershey, “SDR – Half-Baked or Well Done?,” ICASSP 2019. Consulted for the scale-invariant SDR projection/residual definition and the distinction from BSS Eval SDR: <https://arxiv.org/abs/1811.02508>.
- SciPy, [`scipy.signal.resample_poly`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample_poly.html). Consulted for polyphase FIR resampling of non-periodic audio.
- PySoundFile documentation, [`soundfile.read`](https://python-soundfile.readthedocs.io/). Consulted for `always_2d=True` behavior and explicit mono handling.

## Independent review sources

- scikit-learn, [Blind source separation using FastICA](https://scikit-learn.org/stable/auto_examples/decomposition/plot_ica_blind_source_separation.html). Inspected for its noisy non-Gaussian blind-source-separation comparison; it reinforced retaining a PCA baseline alongside ICA rather than presenting whitening as separation.
- scikit-learn, [`_fastica.py`](https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/decomposition/_fastica.py) (main branch inspected 2026-10-14, BSD-3-Clause). Inspected its symmetric decorrelation, parallel fixed-point update, and sign-invariant row-alignment convergence test. No code was reused. It also motivated testing an explicit component-count reduction path for overdetermined observations.
- ComputationalMedicineLab, [`fastica`](https://github.com/ComputationalMedicineLab/fastica) (repository inspected 2026-10-14, MIT). Inspected its documented separation of whitening, ICA, recovery, and projection stages. No code was reused; this project retains its smaller in-process API.
- Meta, [Demucs](https://github.com/facebookresearch/demucs) (repository inspected 2026-10-14, MIT). Inspected only to set scope: it is a trained hybrid waveform/spectrogram music-separation system and is not a comparable classical-ICA baseline. It is not used as a dependency or source of code.

These references informed independent implementations; no third-party algorithm code was reused.
