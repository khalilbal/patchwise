from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass
class AppConfig:
    app_name: str = "Patchwise"
    db_path: str = field(default_factory=lambda: str((_project_root() / ".patchwise" / "patchwise.db").resolve()))
    data_dir: str = field(default_factory=lambda: str((_project_root() / ".patchwise").resolve()))
    timeout_seconds: int = 120
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_model: str = "gpt-4o-mini"


def load_config() -> AppConfig:
    root = _project_root()
    env_path = root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    db_path = Path(os.getenv("PATCHWISE_DB_PATH") or str((root / ".patchwise" / "patchwise.db").resolve()))
    data_dir = Path(os.getenv("PATCHWISE_DATA_DIR") or str((root / ".patchwise").resolve()))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    return AppConfig(
        app_name="Patchwise",
        db_path=str(db_path),
        data_dir=str(data_dir),
        timeout_seconds=int(os.getenv("PATCHWISE_TIMEOUT_SECONDS", "120")),
        ai_api_key=os.getenv("PATCHWISE_AI_API_KEY", ""),
        ai_base_url=os.getenv("PATCHWISE_AI_BASE_URL", ""),
        ai_model=os.getenv("PATCHWISE_AI_MODEL") or "gpt-4o-mini",
    )
