"""The CLI edits the config file in place, and `Settings` reads back exactly what was written."""

from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from whatsapp_extractor.adapters.toml_config import GLOBAL, TomlConfig
from whatsapp_extractor.settings import Settings
from whatsapp_extractor.testing import phones

COMMENTED = """# keep me
account = "5511900000001"   # default account

[watchlist]
chats = ["kept@g.us"]  # also kept
"""


def test_edits_keep_comments_and_unrelated_content(tmp_path: Path) -> None:
    path = tmp_path / "extractor.toml"
    path.write_text(COMMENTED, encoding="utf-8")
    config = TomlConfig(path)
    config.watch("new@g.us", senders=False, account=GLOBAL)
    config.add_account("5511900000002")
    config.set_account("5511900000002")
    text = path.read_text(encoding="utf-8")
    assert "# keep me" in text
    assert "# also kept" in text
    assert 'account = "5511900000002"' in text
    settings = Settings.load(path)
    assert settings.watchlist.chats == {"kept@g.us", "new@g.us"}
    assert "5511900000002" in settings.accounts


def test_a_missing_file_is_created(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "extractor.toml"
    TomlConfig(path).set_account("5511900000001")
    assert Settings.load(path).account == "5511900000001"


def test_add_account_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "extractor.toml"
    config = TomlConfig(path)
    config.add_account("5511900000001")
    config.add_account("5511900000001")
    assert path.read_text(encoding="utf-8").count("5511900000001") == 1


Step = tuple[bool, str, bool]  # (add?, entry, senders?)


@settings(deadline=None, max_examples=40)
@given(
    steps=st.lists(
        st.tuples(
            st.booleans(), st.sampled_from(["a@g.us", "b@g.us", "5511900000009"]), st.booleans()
        ),
        max_size=12,
    ),
    account=st.none() | phones(),
)
def test_the_file_always_reflects_the_sequence_of_edits(
    steps: list[Step], account: str | None
) -> None:
    expected: dict[bool, set[str]] = {False: set(), True: set()}
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "extractor.toml"
        config = TomlConfig(path)
        for add, entry, senders in steps:
            if add:
                config.watch(entry, senders=senders, account=account)
                expected[senders].add(entry)
            else:
                config.unwatch(entry, senders=senders, account=account)
                expected[senders].discard(entry)
        loaded = Settings.load(path)
        watchlist = loaded.watchlist if account is None else loaded.watchlist_for(account)
        if account is not None and not steps:
            return  # nothing written: no account section, so the global (empty) one applies
        assert watchlist.chats == expected[False]
        assert watchlist.senders == expected[True]
