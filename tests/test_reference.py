import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aimusicgen.audio_io import write_wav  # noqa: E402
from aimusicgen.pipeline import GenerateOptions, generate  # noqa: E402
from aimusicgen.reference import analyze_reference, band_levels, match_tonal_balance  # noqa: E402

SR = 44100


def beat_track(bpm=90, secs=20, low=True):
    t = np.arange(secs * SR) / SR
    y = np.zeros_like(t)
    for b in np.arange(0, secs, 60 / bpm):
        i = int(b * SR); n = min(SR // 4, len(y) - i)
        tt = np.arange(n) / SR
        y[i:i + n] += np.sin(2 * np.pi * (55 if low else 1800) * tt) * np.exp(-tt * 12)
    return y.astype(np.float32)


def test_reference_tempo_and_bands(tmp_path):
    p = write_wav(tmp_path / "r.wav", beat_track(90), SR, 16)
    r = analyze_reference(str(p))
    assert abs(r.bpm - 90) <= 1 and len(r.bands_db) == 14


def test_matching_moves_spectrum_toward_reference(tmp_path):
    ref = analyze_reference(str(write_wav(tmp_path / "r.wav", beat_track(90, low=True), SR, 16)))
    bright = np.stack([beat_track(90, low=False)] * 2, axis=1)
    before = band_levels(bright.mean(1), SR)
    after = band_levels(match_tonal_balance(bright, ref, SR).mean(1), SR)
    target = np.array(ref.bands_db)
    assert np.abs(after - target)[4:8].mean() < np.abs(before - target)[4:8].mean()   # low-end bands closer


def test_pipeline_with_reference(tmp_path):
    p = write_wav(tmp_path / "r.wav", beat_track(84), SR, 16)
    r = generate(GenerateOptions(genre="isan", output_dir=str(tmp_path), name="s", bars=4, seed=1, mode="audio",
                                 reference=str(p), soundfont="none"), lambda *a: None)
    assert r.audio_path and Path(r.audio_path).exists()
