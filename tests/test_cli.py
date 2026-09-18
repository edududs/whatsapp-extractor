"""The commands, with the paired accounts faked and everything else real."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from neonize.proto.Neonize_pb2 import JID
from typer.testing import CliRunner

from whatsapp_extractor import cli
from whatsapp_extractor.adapters.neonize_accounts import Account
from whatsapp_extractor.settings import Settings

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

runner = CliRunner()


def paired(*phones: str) -> Callable[[str], list[Account]]:
    """A stand-in for `list_accounts`: the database has exactly these phones paired."""

    def list_accounts(_: str) -> list[Account]:
        return [
            Account(phone=phone, name=f"user {phone}", device=JID(User=f"{phone}:1", Server="s"))
            for phone in phones
        ]

    return list_accounts


@pytest.fixture
def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "extractor.toml"
    monkeypatch.setenv("EXTRACTOR_CONFIG", str(path))
    monkeypatch.setenv("EXTRACTOR_DATABASE", str(tmp_path / "session.db"))
    return path


def test_accounts_marks_the_default(config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "list_accounts", paired("5511900000001", "5511900000002"))
    config.write_text('account = "5511900000002"\n', encoding="utf-8")
    result = runner.invoke(cli.app, ["accounts"])
    assert result.exit_code == 0
    assert "  5511900000001" in result.output
    assert "* 5511900000002" in result.output


def test_account_use_writes_the_default(config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "list_accounts", paired("5511900000001"))
    assert runner.invoke(cli.app, ["account", "use", "5511900000001"]).exit_code == 0
    assert Settings.load(config).account == "5511900000001"


def test_account_use_refuses_an_unpaired_phone(
    config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "list_accounts", paired("5511900000001"))
    result = runner.invoke(cli.app, ["account", "use", "5511900000009"])
    assert result.exit_code == 1
    assert not config.exists()


def test_watch_add_and_remove_edit_the_default_account(config: Path) -> None:
    config.write_text('account = "5511900000001"\n', encoding="utf-8")
    assert runner.invoke(cli.app, ["watch", "add", "g@g.us"]).exit_code == 0
    assert runner.invoke(cli.app, ["watch", "add", "5511900000009", "--sender"]).exit_code == 0
    assert runner.invoke(cli.app, ["watch", "add", "shared@g.us", "--global"]).exit_code == 0
    watchlist = Settings.load(config).watchlist_for("5511900000001")
    assert (watchlist.chats, watchlist.senders) == ({"g@g.us"}, {"5511900000009"})
    assert Settings.load(config).watchlist.chats == {"shared@g.us"}
    assert runner.invoke(cli.app, ["watch", "remove", "g@g.us"]).exit_code == 0
    assert Settings.load(config).watchlist_for("5511900000001").chats == set()


@pytest.mark.usefixtures("config")
def test_watch_add_needs_a_target() -> None:
    result = runner.invoke(cli.app, ["watch", "add", "g@g.us"])
    assert result.exit_code == 1
    assert "--global" in result.output


def test_watch_list_shows_the_effective_watchlist(config: Path) -> None:
    config.write_text(
        '[watchlist]\nchats = ["shared@g.us"]\n'
        '[accounts."5511900000001".watchlist]\nchats = ["own@g.us"]\n',
        encoding="utf-8",
    )
    assert "own@g.us" in runner.invoke(cli.app, ["watch", "list", "-a", "5511900000001"]).output
    assert "shared@g.us" in runner.invoke(cli.app, ["watch", "list", "-a", "5511900000002"]).output
    assert "(empty" not in runner.invoke(cli.app, ["watch", "list"]).output


@pytest.mark.usefixtures("config")
def test_run_without_accounts_asks_to_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "list_accounts", paired())
    result = runner.invoke(cli.app, ["run"])
    assert result.exit_code == 1
    assert "pair" in result.output


@pytest.mark.usefixtures("config")
def test_run_with_several_accounts_and_no_terminal_lists_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "list_accounts", paired("5511900000001", "5511900000002"))
    result = runner.invoke(cli.app, ["run"])
    assert result.exit_code == 1
    assert "5511900000001, 5511900000002" in result.output


@pytest.mark.usefixtures("config")
def test_run_refuses_an_unpaired_account(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "list_accounts", paired("5511900000001"))
    result = runner.invoke(cli.app, ["run", "--account", "5511900000009"])
    assert result.exit_code == 1
    assert "not paired" in result.output
