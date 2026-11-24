"""Runtime settings. Environment variables are read when the app is created."""

import os
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    cors_origins: tuple[str, ...]
    log_level: str
    historical_artifact_dir: Path | None = None


def get_settings() -> Settings:
    configured = os.getenv("SAFARNAMA_ML_ARTIFACT_DIR")
    default = Path(__file__).resolve().parents[3] / "ml" / "outputs"
    directory = default if configured is None else (Path(configured) if configured.strip() else None)
    return Settings(
        database_url=os.getenv("SAFARNAMA_DATABASE_URL", "sqlite:///./data/safarnama.db"),
        cors_origins=tuple(
            origin.strip()
            for origin in os.getenv(
                "SAFARNAMA_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if origin.strip()
        ),
        historical_artifact_dir=directory,
        log_level=os.getenv("SAFARNAMA_LOG_LEVEL", "INFO").upper(),
    )
