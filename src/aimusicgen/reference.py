"""Match the sound of a reference track: tempo and long-term tonal balance (what can be measured from audio).
It does NOT copy melodies, chords or the instruments themselves."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .audio_io import read_audio
from .fx import _fft_shape

EDGES = np.array([20, 30, 40, 50, 60, 80, 100, 150, 250, 500, 1000, 2000, 4000, 8000, 16000], float)


@dataclass
class RefProfile:
    bpm: float
    bands_db: list[float]      # energy per band, relative to the total
    rms_db: float
    crest_db: float
    seconds: float


def band_levels(mono: np.ndarray, sr: int) -> np.ndarray:
    n = 1 << 15
    w = np.hanning(n)
    ps = np.zeros(n // 2 + 1)
    step = n * 2 if len(mono) > n * 8 else n // 2
    for i in range(0, max(1, len(mono) - n), step):
        seg = mono[i:i + n]
        ps += np.abs(np.fft.rfft(np.pad(seg, (0, n - len(seg))) * w)) ** 2
    f = np.fft.rfftfreq(n, 1 / sr)
    tot = ps[(f >= EDGES[0]) & (f < EDGES[-1])].sum() + 1e-20
    return np.array([10 * np.log10(ps[(f >= a) & (f < b)].sum() / tot + 1e-12) for a, b in zip(EDGES, EDGES[1:])])


def estimate_bpm(mono: np.ndarray, sr: int, lo: float = 70, hi: float = 135) -> float:
    hop, n = 512, 1024
    win = np.hanning(n)
    mag = np.abs(np.stack([np.fft.rfft(mono[i:i + n] * win) for i in range(0, len(mono) - n, hop)]))
    flux = np.diff(mag, axis=0).clip(0).sum(1)
    flux -= flux.mean()
    ac = np.correlate(flux, flux, "full")[len(flux) - 1:]
    fps = sr / hop
    lags = np.arange(int(fps * 60 / 200), int(fps * 60 / 55))
    sc = ac[lags] / np.maximum(1, len(flux) - lags)
    best = {}
    for lag, s in zip(lags, sc):
        b = 60 * fps / lag
        while b > hi:
            b /= 2
        while b < lo:
            b *= 2
        best[round(b)] = best.get(round(b), 0) + max(s, 0)
    return float(max(best, key=best.get))


def analyze_reference(path: str, max_seconds: float = 240) -> RefProfile:
    x, sr = read_audio(path)
    m = x.mean(axis=1)[: int(max_seconds * sr)]
    if len(m) < sr * 5:
        raise ValueError("Reference is too short (need at least 5 seconds)")
    rms = float(np.sqrt((m ** 2).mean()) + 1e-9)
    return RefProfile(estimate_bpm(m, sr), band_levels(m, sr).round(2).tolist(), 20 * np.log10(rms),
                      20 * np.log10(np.abs(m).max() / rms), len(m) / sr)


# how strongly each band follows the reference. Mid bands hold the vocal in a full mix, so they follow less.
_STRENGTH = np.array([0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.5, 0.3, 0.3, 0.3, 0.6, 0.8])


def match_tonal_balance(accomp: np.ndarray, ref: RefProfile, sr: int, max_db: float = 9.0) -> np.ndarray:
    """EQ the accompaniment (n, 2) toward the reference's long-term spectrum (zero-phase, smooth, limited to +-max_db)."""
    cur = band_levels(accomp.mean(axis=1), sr)
    diff = (np.array(ref.bands_db) - cur) * _STRENGTH
    diff -= np.median(diff)                      # overall level is handled elsewhere
    diff = np.clip(diff, -max_db, max_db)
    centers = np.sqrt(EDGES[:-1] * EDGES[1:])
    lc = np.log2(centers)

    def gain(f):
        g = np.interp(np.log2(np.maximum(f, 1.0)), lc, diff)       # smooth in log-frequency
        return 10 ** (g / 20)

    return _fft_shape(accomp, gain, sr)
