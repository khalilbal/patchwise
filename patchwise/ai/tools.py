from __future__ import annotations

from pathlib import Path


def read_limited_source(path: str | Path, max_lines: int = 80) -> str:
    target = Path(path)
    if not target.exists():
        return ""
    lines = target.read_text(encoding="utf-8", errors="ignore").splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    return "\n".join(lines)
