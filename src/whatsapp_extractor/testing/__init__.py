"""Test kit for the pieces: factories, Hypothesis strategies and port contracts.

Needs the `testing` extra. Adapter authors inherit a contract class in their test module,
implement its one abstract method, and pytest collects the properties that every
implementation of that port must hold.
"""

from .contracts import MessageStoreContract
from .factories import ALICE, GROUP, make_message
from .strategies import (
    chats,
    contents,
    group_jids,
    jids,
    lid_jids,
    media,
    message_ids,
    messages,
    phone_jids,
    phones,
    senders,
    texts,
    watchlists,
)

__all__ = [
    "ALICE",
    "GROUP",
    "MessageStoreContract",
    "chats",
    "contents",
    "group_jids",
    "jids",
    "lid_jids",
    "make_message",
    "media",
    "message_ids",
    "messages",
    "phone_jids",
    "phones",
    "senders",
    "texts",
    "watchlists",
]
