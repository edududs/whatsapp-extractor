from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from .domain import Watchlist


class StoreKind(StrEnum):
    MEMORY = "memory"
    JSONL = "jsonl"
    SQL = "sql"


class ViewKind(StrEnum):
    PANEL = "panel"
    JSON = "json"
    LOG = "log"


class Settings(BaseSettings):
    """Read from `EXTRACTOR_*` environment variables and `.env`. See `.env.example`."""

    model_config = SettingsConfigDict(
        env_prefix="EXTRACTOR_",
        env_file=".env",
        env_nested_delimiter="__",
        frozen=True,
        use_attribute_docstrings=True,
    )

    database: str = "session.db"
    """SQLite file or `postgres://` DSN shared by neonize (pairing, contacts) and the
    `messages` table. It holds the WhatsApp credentials."""
    watchlist: Watchlist = Watchlist()
    store: StoreKind = StoreKind.SQL
    jsonl_path: Path = Path("messages.jsonl")
    buffer_size: int = 10_000
    view: ViewKind = ViewKind.PANEL
    """How extracted messages are shown. `panel` and `json` need the `rich` extra."""
