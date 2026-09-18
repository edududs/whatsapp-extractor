from __future__ import annotations

from hypothesis import given

from whatsapp_extractor import Watchlist
from whatsapp_extractor.bootstrap import describe
from whatsapp_extractor.testing import watchlists


def test_an_empty_watchlist_is_described_as_everything() -> None:
    assert describe(Watchlist()) == "watching every chat and sender"


@given(watchlist=watchlists())
def test_every_watched_entry_appears_in_the_description(watchlist: Watchlist) -> None:
    text = describe(watchlist)
    for entry in watchlist.chats | watchlist.senders:
        assert repr(entry) in text or text == "watching every chat and sender"
