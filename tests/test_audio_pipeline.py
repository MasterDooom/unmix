import numpy as np
import pytest
import soundfile as sf

from unmix.audio import AudioBuffer, load_audio, load_sources, resample_audio, write_audio
from unmix.pipeline import run_audio_separation, separate_mixtures


def test_audio_round_trip_and_multichannel_policy(tmp_path) -> None:
    path = write_audio(tmp_path / "mono.wav", np.array([0.0, 2.0, -2.0]), 8000)
    loaded = load_audio(path)
    assert loaded.sample_rate == 8000
    assert loaded.samples.shape == (3,)
    assert np.max(np.abs(loaded.samples)) <= 0.991
    sf.write(tmp_path / "stereo.wav", np.column_stack([loaded.samples, loaded.samples]), 8000)
    with pytest.raises(ValueError):
        load_audio(tmp_path / "stereo.wav")
    assert load_audio(tmp_path / "stereo.wav", channel_policy="mixdown").samples.shape == (3,)


def test_resampling_alignment_and_pipeline(tmp_path) -> None:
    rng = np.random.default_rng(123)
    first = write_audio(tmp_path / "first.wav", rng.laplace(size=1000), 8000)
    second = write_audio(tmp_path / "second.wav", rng.uniform(-1, 1, size=700), 4000)
    sources, rate = load_sources([first, second], sample_rate=8000)
    assert rate == 8000
    assert sources.shape == (2, 1000)
    assert resample_audio(AudioBuffer(np.ones(5), 4000), 8000).samples.size >= 9
    run = run_audio_separation([first, second], np.array([[1.0, 0.2], [0.3, 1.0]]), tmp_path / "run")
    assert run.mixture_path.is_file()
    assert all(path.is_file() and path.stat().st_size > 0 for path in run.component_paths)
    assert run.ica.converged
    assert run.metrics.mean_absolute_correlation > 0.95
    assert separate_mixtures(np.vstack([sources[0], sources[1]])).sources.shape == sources.shape
