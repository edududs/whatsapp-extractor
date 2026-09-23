# ruff: noqa: INP001 — a one-off script, not part of the `whatsapp_extractor` package
"""Render sample terminal outputs for the README, one image per view.

Uses the package's real rendering code (`rich_view.render_panel`, `rich_view.render_json`,
`log_handler.log_message_extracted`) against fake but realistic `Message` data, captured with
`rich.console.Console(record=True)` and exported to SVG. Never run against a real account.

Usage: uv run --no-sync python scripts/render_samples.py
"""

from __future__ import annotations

import asyncio
import io
import logging
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from whatsapp_extractor.adapters.log_handler import log_message_extracted
from whatsapp_extractor.adapters.rich_view import Renderer, message_view, render_json, render_panel
from whatsapp_extractor.bootstrap import describe
from whatsapp_extractor.domain import (
    Chat,
    ChatKind,
    Content,
    Jid,
    Media,
    MediaKind,
    Message,
    MessageExtracted,
    MessageKind,
    Sender,
    Watchlist,
)

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "images"
CONSOLE_WIDTH = 100

# Fictitious JIDs and phone numbers only: no real WhatsApp account is contacted.
GROUP = Jid(user="120363012345678901", server="g.us")
CARLOS = Jid(user="556199220002", server="s.whatsapp.net")
MARCOS = Jid(user="5561991110001", server="s.whatsapp.net")
ANA = Jid(user="5561991110002", server="s.whatsapp.net")
OWNER = Jid(user="5561998887777", server="s.whatsapp.net")

GROUP_CHAT = Chat(jid=GROUP, kind=ChatKind.GROUP, name="Caronas Brazlândia ⇄ Plano")
DIRECT_CHAT = Chat(
    jid=CARLOS,
    kind=ChatKind.DIRECT,
    counterpart_phone=CARLOS.phone,
    name="Carlos Mendes",
)


def _ts(day: int, hour: int, minute: int) -> datetime:
    return datetime(2026, 9, day, hour, minute, tzinfo=UTC)


def sample_messages() -> list[Message]:
    """Five to seven fictitious messages: group ride-share chat, a direct chat, one outgoing
    reply, one image with a caption, and one voice note.
    """
    return [
        Message(
            id="3EB0ABC1",
            timestamp=_ts(20, 9, 15),
            kind=MessageKind.TEXT,
            from_me=False,
            chat=GROUP_CHAT,
            sender=Sender(jid=MARCOS, phone=MARCOS.phone, pushname="Marcos Vinícius"),
            content=Content(text="Saindo de Brazlândia 6h, 2 vagas, R$ 15"),
        ),
        Message(
            id="3EB0ABC2",
            timestamp=_ts(20, 9, 20),
            kind=MessageKind.TEXT,
            from_me=False,
            chat=GROUP_CHAT,
            sender=Sender(jid=ANA, phone=ANA.phone, pushname="Ana Paula"),
            content=Content(text="Alguém indo pro Plano às 18h?"),
        ),
        Message(
            id="3EB0ABC3",
            timestamp=_ts(20, 9, 22),
            kind=MessageKind.TEXT,
            from_me=True,
            chat=GROUP_CHAT,
            sender=Sender(jid=OWNER, phone=OWNER.phone, pushname=""),
            content=Content(text="Consigo levar 1 vaga às 18h10, saída do Taguaparque"),
        ),
        Message(
            id="3EB0ABC4",
            timestamp=_ts(20, 9, 30),
            kind=MessageKind.MEDIA,
            from_me=False,
            chat=GROUP_CHAT,
            sender=Sender(jid=MARCOS, phone=MARCOS.phone, pushname="Marcos Vinícius"),
            content=Content(
                text="Ponto de encontro, chegar 10 min antes",
                media=Media(
                    kind=MediaKind.IMAGE,
                    mimetype="image/jpeg",
                    caption="Ponto de encontro, chegar 10 min antes",
                    width=1280,
                    height=960,
                    file_length=184_320,
                    file_name="ponto-encontro.jpg",
                ),
            ),
        ),
        Message(
            id="3EB0ABC5",
            timestamp=_ts(20, 9, 32),
            kind=MessageKind.MEDIA,
            from_me=False,
            chat=GROUP_CHAT,
            sender=Sender(jid=ANA, phone=ANA.phone, pushname="Ana Paula"),
            content=Content(
                media=Media(
                    kind=MediaKind.AUDIO,
                    mimetype="audio/ogg; codecs=opus",
                    duration_seconds=47,
                    file_length=94_512,
                    is_voice_note=True,
                ),
            ),
        ),
        Message(
            id="3EB0ABC6",
            timestamp=_ts(21, 7, 5),
            kind=MessageKind.TEXT,
            from_me=False,
            chat=DIRECT_CHAT,
            sender=Sender(jid=CARLOS, phone=CARLOS.phone, pushname="Carlos Mendes"),
            content=Content(text="Bom dia! Confirmando a carona de amanhã 7h?"),
        ),
        Message(
            id="3EB0ABC7",
            timestamp=_ts(21, 7, 10),
            kind=MessageKind.TEXT,
            from_me=True,
            chat=DIRECT_CHAT,
            sender=Sender(jid=OWNER, phone=OWNER.phone, pushname=""),
            content=Content(text="Bom dia Carlos! Confirmado, te pego às 7h na parada."),
        ),
    ]


def _events(messages: list[Message]) -> list[MessageExtracted]:
    return [MessageExtracted(message=message) for message in messages]


def _new_console() -> Console:
    # `file` is an in-memory sink: we only want the SVG the recording produces, never a live
    # write to the real stdout (whose Windows console encoding chokes on non-ASCII glyphs).
    return Console(
        record=True,
        width=CONSOLE_WIDTH,
        force_terminal=True,
        legacy_windows=False,
        file=io.StringIO(),
    )


async def _render_view(console: Console, render: Renderer, messages: list[Message]) -> None:
    handler = message_view(console, render)
    for event in _events(messages):
        await handler(event)


async def render_panel_svg(messages: list[Message]) -> Console:
    console = _new_console()
    await _render_view(console, render_panel, messages)
    return console


async def render_json_svg(messages: list[Message]) -> Console:
    console = _new_console()
    await _render_view(console, render_json, messages)
    return console


async def render_log_svg(messages: list[Message]) -> Console:
    console = _new_console()
    handler = RichHandler(console=console, show_path=False)
    logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[handler], force=True)

    bootstrap_log = logging.getLogger("whatsapp_extractor.bootstrap")
    watchlist = Watchlist(chats=frozenset({GROUP.value, CARLOS.phone or ""}))
    bootstrap_log.info("account %s: %s", OWNER.phone, describe(watchlist))

    for event in _events(messages):
        await log_message_extracted(event)
    return console


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    messages = sample_messages()
    # JSON and log stay short so the SVGs remain a reasonable height: JSON keeps one plain-text
    # message and one media message; log keeps the startup line plus the first four messages.
    json_messages = [messages[0], messages[3]]
    log_messages = messages[:4]

    panel_console = await render_panel_svg(messages)
    json_console = await render_json_svg(json_messages)
    log_console = await render_log_svg(log_messages)

    targets = {
        "panel": (panel_console, OUT_DIR / "view-panel.svg"),
        "json": (json_console, OUT_DIR / "view-json.svg"),
        "log": (log_console, OUT_DIR / "view-log.svg"),
    }
    for name, (console, path) in targets.items():
        console.save_svg(str(path), title="whatsapp-extractor run")
        print(f"wrote {name} view -> {path}")  # noqa: T201 — reporting output paths is the point


if __name__ == "__main__":
    asyncio.run(main())
