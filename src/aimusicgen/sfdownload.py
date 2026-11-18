"""Download a free General-MIDI SoundFont (real sampled instruments) on the user's machine."""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path

# GeneralUser GS (free licence, ~30 MB). Mirrors are tried in order.
URLS = [
    "https://github.com/mrbumpy409/GeneralUser-GS/raw/main/GeneralUser-GS.sf2",
    "https://raw.githubusercontent.com/mrbumpy409/GeneralUser-GS/main/GeneralUser-GS.sf2",
]
FILENAME = "GeneralUser-GS.sf2"
MANUAL = "https://github.com/mrbumpy409/GeneralUser-GS"


def user_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "AIMusicGenerator" / "soundfonts"


def download_soundfont(dest_dir: Path | None = None, urls: list[str] | None = None, progress=lambda f, m: None) -> Path:
    dest_dir = Path(dest_dir or user_dir())
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / FILENAME
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return dest
    errors = []
    for url in (urls or URLS):
        tmp = dest.with_suffix(".part")
        try:
            progress(0.0, "Downloading SoundFont...")
            with urllib.request.urlopen(url, timeout=30) as r, open(tmp, "wb") as f:
                total = int(r.headers.get("Content-Length") or 0)
                got = 0
                while chunk := r.read(1 << 18):
                    f.write(chunk)
                    got += len(chunk)
                    if total:
                        progress(got / total, f"Downloading SoundFont... {got // 1_000_000} MB")
            with open(tmp, "rb") as f:
                head = f.read(12)
            if head[:4] != b"RIFF" or head[8:12] != b"sfbk":
                raise ValueError("downloaded file is not a SoundFont")
            tmp.replace(dest)
            return dest
        except Exception as e:  # try the next mirror
            errors.append(f"{url}: {e}")
            tmp.unlink(missing_ok=True)
    raise RuntimeError("Could not download the SoundFont.\n" + "\n".join(errors) +
                       f"\nDownload a .sf2 manually from {MANUAL} and put it in: {dest_dir}")
