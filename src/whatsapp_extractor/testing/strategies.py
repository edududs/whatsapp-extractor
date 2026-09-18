"""Hypothesis strategies for every domain object, so tests state properties, not examples."""

from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import strategies as st

from whatsapp_extractor.domain import (
    Chat,
    ChatKind,
    Content,
    Jid,
    Media,
    MediaKind,
    Message,
    MessageKind,
    Sender,
    Watchlist,
)
from whatsapp_extractor.domain.jid import (
    BROADCAST_SERVER,
    GROUP_SERVER,
    LID_SERVER,
    NEWSLETTER_SERVER,
    PHONE_SERVER,
    STATUS_USER,
)


def texts(max_size: int | None = None) -> st.SearchStrategy[str]:
    """Any text a message can carry: full Unicode minus lone surrogates, which JSON rejects."""
    return st.text(alphabet=st.characters(exclude_categories=("Cs",)), max_size=max_size)


def phones() -> st.SearchStrategy[str]:
    return st.from_regex(r"\A[1-9][0-9]{9,14}\Z")


def message_ids() -> st.SearchStrategy[str]:
    return st.from_regex(r"\A[0-9A-F]{16,32}\Z")


def phone_jids() -> st.SearchStrategy[Jid]:
    return st.builds(Jid, user=phones(), server=st.just(PHONE_SERVER))


def lid_jids() -> st.SearchStrategy[Jid]:
    return st.builds(Jid, user=st.from_regex(r"\A[0-9]{12,16}\Z"), server=st.just(LID_SERVER))


def group_jids() -> st.SearchStrategy[Jid]:
    return st.builds(Jid, user=st.from_regex(r"\A[0-9]{18}\Z"), server=st.just(GROUP_SERVER))


def jids() -> st.SearchStrategy[Jid]:
    """Every kind of address, including servers this piece does not know."""
    known = st.sampled_from([NEWSLETTER_SERVER, BROADCAST_SERVER])
    unknown = st.from_regex(r"\A[a-z]{2,10}\.[a-z]{2,4}\Z")
    return st.one_of(
        phone_jids(),
        lid_jids(),
        group_jids(),
        st.just(Jid(user=STATUS_USER, server=BROADCAST_SERVER)),
        st.builds(Jid, user=phones(), server=st.one_of(known, unknown)),
    )


@st.composite
def chats(draw: st.DrawFn) -> Chat:
    jid = draw(jids())
    kind = ChatKind.of(jid)
    direct = kind is ChatKind.DIRECT
    return Chat(
        jid=jid,
        kind=kind,
        counterpart_phone=draw(st.none() | phones()) if direct else None,
        name=draw(st.none() | texts(max_size=40)),
    )


@st.composite
def senders(draw: st.DrawFn) -> Sender:
    jid = draw(st.one_of(phone_jids(), lid_jids()))
    return Sender(
        jid=jid,
        lid=jid.lid or draw(st.none() | st.from_regex(r"\A[0-9]{12,16}\Z")),
        phone=jid.phone or draw(st.none() | phones()),
        pushname=draw(texts(max_size=40)),
    )


def media() -> st.SearchStrategy[Media]:
    positive = st.none() | st.integers(min_value=1, max_value=2**31)
    return st.builds(
        Media,
        kind=st.sampled_from(MediaKind),
        mimetype=st.from_regex(r"\A[a-z]+/[a-z0-9.+-]+\Z"),
        caption=st.none() | texts(max_size=200),
        duration_seconds=positive,
        width=positive,
        height=positive,
        file_length=positive,
        file_name=st.none() | texts(max_size=40),
        is_voice_note=st.none() | st.booleans(),
    )


def contents() -> st.SearchStrategy[Content]:
    return st.builds(Content, text=texts(max_size=500), media=st.none() | media())


def messages() -> st.SearchStrategy[Message]:
    # Local-time rendering of dates before 1970 fails on Windows; real messages are recent anyway.
    timestamps = st.datetimes(
        min_value=datetime(2010, 1, 1),  # noqa: DTZ001 — hypothesis attaches the timezone
        max_value=datetime(2100, 1, 1),  # noqa: DTZ001
        timezones=st.just(UTC),
    )
    return st.builds(
        Message,
        id=message_ids(),
        timestamp=timestamps,
        kind=st.sampled_from(MessageKind),
        from_me=st.booleans(),
        chat=chats(),
        sender=senders(),
        recipient=st.none() | phone_jids() | lid_jids(),
        content=contents(),
        is_ephemeral=st.booleans(),
        is_view_once=st.booleans(),
        is_edit=st.booleans(),
    )


def watchlists() -> st.SearchStrategy[Watchlist]:
    entries = st.frozensets(texts(max_size=40), max_size=5)
    return st.builds(Watchlist, chats=entries, senders=entries)
