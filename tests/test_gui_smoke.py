import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(__import__("importlib.util").util.find_spec("tkinter") is None, reason="no tkinter")
@pytest.mark.skipif(not shutil.which("xvfb-run") and not os.environ.get("DISPLAY") and sys.platform != "win32",
                    reason="no display")
def test_gui_builds_and_collects_options():
    code = ("import sys; sys.path.insert(0, r'%s')\n"
            ""
            "from aimusicgen.gui import App\n"
            "a = App(); o = a.options(); print('OK', o.soundfont); a.destroy()\n" % (ROOT / "src"))
    cmd = [sys.executable, "-c", code]
    if sys.platform != "win32" and not os.environ.get("DISPLAY"):
        cmd = ["xvfb-run", "-a"] + cmd
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert "OK" in r.stdout, r.stderr[-800:]
