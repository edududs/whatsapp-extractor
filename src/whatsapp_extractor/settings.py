"""Configuration lives in a TOML file; the environment holds secrets and deployment overrides.

Precedence, highest first: explicit arguments (CLI flags), environment, `.env`, the TOML
file, defaults. The file is `extractor.toml` in the working directory unless `config`
(`EXTRACTOR_CONFIG`) says otherwise.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from .domain import Watchlist
from .domain.base import FrozenModel

DEFAULT_CONFIG_FILE = Path("extractor.toml")


class StoreKind(StrEnum):
    MEMORY = "memory"
    JSONL = "jsonl"
    SQL = "sql"


class ViewKind(StrEnum):
    PANEL = "panel"
    JSON = "json"
    LOG = "log"


class AccountSettings(FrozenModel):
    watchlist: Watchlist | None = None
    """Replaces the global watchlist for this account when present."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EXTRACTOR_",
        env_file=".env",
        env_nested_delimiter="__",
        frozen=True,
        use_attribute_docstrings=True,
    )

    config: Path = DEFAULT_CONFIG_FILE
    """The TOML file everything below is read from. Only meaningful as an argument or env."""
    database: str = "session.db"
    """SQLite file or `postgres://` DSN shared by neonize (pairing, contacts) and the
    per-account message schemas. It holds the WhatsApp credentials."""
    messages_database: str | None = None
    """Where the per-account message schemas live when not in `database`, e.g. to keep
    the WhatsApp credentials on a local SQLite file and the messages on a server."""
    account: str | None = Field(default=None, pattern=r"^[0-9]{5,15}$")
    """Phone of the paired account to run as. Optional when only one is paired."""
    watchlist: Watchlist = Watchlist()
    """Applies to every account without a watchlist of its own."""
    accounts: Mapping[str, AccountSettings] = Field(default_factory=dict)
    """Per-account overrides, keyed by phone."""
    store: StoreKind = StoreKind.SQL
    jsonl_path: str = "messages_{account}.jsonl"
    """Path template for the `jsonl` store; `{account}` becomes the phone."""
    buffer_size: int = 10_000
    view: ViewKind = ViewKind.PANEL
    """How extracted messages are shown. `panel` and `json` need the `rich` extra."""

    @field_validator("account", mode="before")
    @classmethod
    def blank_means_unset(cls, value: object) -> object:
        """`EXTRACTOR_ACCOUNT=` in a `.env` is how one leaves it unset."""
        return None if value == "" else value

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # The TOML path must be known before the file is read: peek at the higher sources.
        given = {**dotenv_settings(), **env_settings(), **init_settings()}
        toml_file = Path(given.get("config") or DEFAULT_CONFIG_FILE)
        toml = TomlConfigSettingsSource(settings_cls, toml_file=toml_file)
        return (init_settings, env_settings, dotenv_settings, toml, file_secret_settings)

    @classmethod
    def load(cls, config: Path | None = None, **overrides: object) -> Self:
        """Read from `config` (default: env or `extractor.toml`), with `overrides` winning."""
        if config is not None:
            overrides["config"] = config
        return cls(**overrides)  # pyright: ignore[reportArgumentType] — kwargs are validated

    @property
    def message_database(self) -> str:
        return self.messages_database or self.database

    def watchlist_for(self, account: str) -> Watchlist:
        """The account's own watchlist, else the global one."""
        own = self.accounts.get(account)
        return own.watchlist if own and own.watchlist is not None else self.watchlist

    def jsonl_path_for(self, account: str) -> Path:
        return Path(self.jsonl_path.format(account=account))
