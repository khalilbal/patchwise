from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence


def run_command(args: Sequence[str], cwd: str | Path, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
    )
