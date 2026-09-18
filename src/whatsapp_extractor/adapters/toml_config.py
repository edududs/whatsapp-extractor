"""Edits the configuration file the way `uv add` edits pyproject: in place, keeping comments.

The file is the source of truth for configuration; only the commands here write to it.
Reading goes through `Settings`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import tomlkit
from tomlkit.items import Array, Table

if TYPE_CHECKING:
    from pathlib import Path

GLOBAL = None
"""Target the top-level `[watchlist]` instead of an account."""


class TomlConfig:
    def __init__(self, path: Path) -> None:
        self._path = path

    def set_account(self, phone: str) -> None:
        """The account `run` uses when none is given."""
        document = self._read()
        document["account"] = phone
        self._write(document)

    def add_account(self, phone: str) -> None:
        """Make sure `[accounts."<phone>"]` exists. Idempotent."""
        document = self._read()
        self._account_table(document, phone)
        self._write(document)

    def watch(self, entry: str, *, senders: bool, account: str | None) -> None:
        document = self._read()
        entries = self._entries(document, account, senders=senders)
        if entry not in entries:
            entries.append(entry)
        self._write(document)

    def unwatch(self, entry: str, *, senders: bool, account: str | None) -> None:
        document = self._read()
        entries = self._entries(document, account, senders=senders)
        if entry in entries:
            entries.remove(entry)
        self._write(document)

    def _entries(
        self, document: tomlkit.TOMLDocument, account: str | None, *, senders: bool
    ) -> list[str]:
        owner = document if account is None else self._account_table(document, account)
        watchlist = _table(owner, "watchlist")
        key = "senders" if senders else "chats"
        if key not in watchlist:
            watchlist[key] = tomlkit.array()
        entries = watchlist[key]
        if not isinstance(entries, Array):
            msg = f"`{key}` must be an array in {self._path}"
            raise TypeError(msg)
        return cast("list[str]", entries)  # an Array is a list that keeps its formatting

    @staticmethod
    def _account_table(document: tomlkit.TOMLDocument, phone: str) -> Table:
        accounts = _table(document, "accounts", super_table=True)
        return _table(accounts, phone)

    def _read(self) -> tomlkit.TOMLDocument:
        if not self._path.exists():
            return tomlkit.document()
        return tomlkit.parse(self._path.read_text(encoding="utf-8"))

    def _write(self, document: tomlkit.TOMLDocument) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(tomlkit.dumps(document), encoding="utf-8")


def _table(owner: tomlkit.TOMLDocument | Table, key: str, *, super_table: bool = False) -> Table:
    if key not in owner:
        owner[key] = tomlkit.table(is_super_table=super_table)
    table = owner[key]
    if not isinstance(table, Table):
        msg = f"`{key}` must be a table"
        raise TypeError(msg)
    return table
