"""Where configuration comes from, and who wins."""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from whatsapp_extractor import Watchlist
from whatsapp_extractor.settings import AccountSettings, Settings, StoreKind
from whatsapp_extractor.testing import phones, watchlists

TOML = """
account = "5511900000001"
store = "jsonl"

[watchlist]
chats = ["global@g.us"]

[accounts."5511900000001".watchlist]
chats = ["mine@g.us"]
senders = ["5511900000009"]

[accounts."5511900000002"]
"""


@pytest.fixture
def config(tmp_path: Path) -> Path:
    path = tmp_path / "extractor.toml"
    path.write_text(TOML, encoding="utf-8")
    return path


def test_the_toml_file_is_read(config: Path) -> None:
    settings = Settings.load(config)
    assert settings.account == "5511900000001"
    assert settings.store is StoreKind.JSONL
    assert settings.watchlist.chats == {"global@g.us"}
    assert set(settings.accounts) == {"5511900000001", "5511900000002"}


def test_environment_beats_the_file_and_arguments_beat_both(
    config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EXTRACTOR_STORE", "sql")
    assert Settings.load(config).store is StoreKind.SQL
    assert Settings.load(config, store="memory").store is StoreKind.MEMORY


def test_a_missing_file_means_defaults(tmp_path: Path) -> None:
    settings = Settings.load(tmp_path / "absent.toml")
    assert settings.account is None
    assert settings.watchlist == Watchlist()


def test_config_path_comes_from_the_environment(
    config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EXTRACTOR_CONFIG", str(config))
    assert Settings().account == "5511900000001"


def test_an_account_with_its_own_watchlist_replaces_the_global_one(config: Path) -> None:
    settings = Settings.load(config)
    assert settings.watchlist_for("5511900000001").chats == {"mine@g.us"}
    assert settings.watchlist_for("5511900000002").chats == {"global@g.us"}
    assert settings.watchlist_for("5511900000003").chats == {"global@g.us"}


@given(shared=watchlists(), own=st.none() | watchlists(), phone=phones(), other=phones())
def test_watchlist_for_is_the_own_one_iff_the_account_declares_one(
    shared: Watchlist, own: Watchlist | None, phone: str, other: str
) -> None:
    settings = Settings.load(
        None,
        watchlist=shared,
        accounts={phone: AccountSettings(watchlist=own)},
    )
    assert settings.watchlist_for(phone) == (own if own is not None else shared)
    if other != phone:
        assert settings.watchlist_for(other) == shared


@given(phone=phones())
def test_jsonl_path_is_per_account(phone: str) -> None:
    assert Settings.load(None).jsonl_path_for(phone).name == f"messages_{phone}.jsonl"


@given(
    account=st.text(min_size=1, max_size=20).filter(
        lambda s: not s.isdigit() or not 5 <= len(s) <= 15
    )
)
def test_account_must_be_a_phone_unless_blank(account: str) -> None:
    with pytest.raises(ValueError, match="account"):
        Settings.load(None, account=account)


def test_a_dotenv_copied_from_the_example_loads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`EXTRACTOR_ACCOUNT=` left blank means unset; `EXTRACTOR_CONFIG` in `.env` is honoured."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "custom.toml").write_text('store = "memory"\n', encoding="utf-8")
    (tmp_path / ".env").write_text(
        "EXTRACTOR_DATABASE=session.db\nEXTRACTOR_ACCOUNT=\nEXTRACTOR_CONFIG=custom.toml\n",
        encoding="utf-8",
    )
    settings = Settings()
    assert settings.account is None
    assert settings.config == Path("custom.toml")
    assert settings.store is StoreKind.MEMORY


def test_an_explicit_config_beats_the_environment(
    config: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = tmp_path / "other.toml"
    other.write_text('account = "5511900000009"\n', encoding="utf-8")
    monkeypatch.setenv("EXTRACTOR_CONFIG", str(config))
    assert Settings.load(other).account == "5511900000009"


def test_messages_default_to_the_session_database_unless_told_otherwise(tmp_path: Path) -> None:
    assert Settings.load(tmp_path / "none.toml").message_database == "session.db"
    apart = Settings.load(tmp_path / "none.toml", messages_database="postgres://u:p@h/db")
    assert apart.database == "session.db"
    assert apart.message_database == "postgres://u:p@h/db"


def test_a_blank_messages_database_means_the_session_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("EXTRACTOR_MESSAGES_DATABASE=\n", encoding="utf-8")
    assert Settings().message_database == "session.db"
