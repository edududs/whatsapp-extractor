"""Presentation adapter: draws each extracted message on a rich console. Needs the `rich` extra.

Everything that comes from WhatsApp goes through `Text`, never through markup strings:
a message saying `[red]` must be shown, not interpreted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Group
from rich.filesize import decimal
from rich.json import JSON
from rich.panel import Panel
from rich.text import Text

from whatsapp_extractor.domain import ChatKind

if TYPE_CHECKING:
    from collections.abc import Callable

    from rich.console import Console, RenderableType

    from whatsapp_extractor.application import EventHandler
    from whatsapp_extractor.domain import Media, Message, MessageExtracted

type Renderer = Callable[[Message], RenderableType]

_BORDER_BY_CHAT_KIND = {
    ChatKind.DIRECT: "green",
    ChatKind.GROUP: "blue",
    ChatKind.STATUS: "magenta",
    ChatKind.BROADCAST: "yellow",
    ChatKind.NEWSLETTER: "yellow",
    ChatKind.UNKNOWN: "white",
}


def message_view(console: Console, render: Renderer) -> EventHandler[MessageExtracted]:
    async def show(event: MessageExtracted) -> None:
        console.print(render(event.message))

    return show


def render_panel(message: Message) -> Panel:
    """What was said: the text and a one-line media summary."""
    content = message.content
    lines = [Text(content.text)] if content.text else []
    if content.media:
        lines.append(_media_summary(content.media))
    return _frame(message, Group(*lines) if lines else Text("(no content)", style="dim"))


def render_json(message: Message) -> Panel:
    """Everything that was mapped, for inspecting the extraction itself."""
    return _frame(message, JSON(message.model_dump_json()))


def _frame(message: Message, body: RenderableType) -> Panel:
    chat, sender = message.chat, message.sender
    border = _BORDER_BY_CHAT_KIND[chat.kind]
    who = "me" if message.from_me else sender.pushname or "?"
    title = Text.assemble(
        (f"{message.timestamp.astimezone():%H:%M:%S} ", "dim"),
        (f"{chat.kind.value.upper()} ", f"bold {border}"),
        (f"{chat.name} " if chat.name else "", "bold"),
        (chat.counterpart_phone or chat.jid.value, border),
        ("  ◂  ", "dim"),
        (who, "bold"),
        (f" {sender.phone or sender.lid or sender.jid.value}", "dim"),
    )
    flags = [
        name
        for name, active in (
            ("ephemeral", message.is_ephemeral),
            ("view once", message.is_view_once),
            ("edit", message.is_edit),
        )
        if active
    ]
    subtitle = Text(" · ".join([message.kind.value, *flags, message.id]), style="dim")
    return Panel(
        body,
        title=title,
        title_align="left",
        subtitle=subtitle,
        subtitle_align="right",
        border_style=border,
    )


def _media_summary(media: Media) -> Text:
    minutes, seconds = divmod(media.duration_seconds or 0, 60)
    parts = [
        "voice note" if media.is_voice_note else media.kind.value,
        media.file_name,
        media.mimetype,
        f"{media.width}x{media.height}" if media.width and media.height else None,
        f"{minutes}:{seconds:02d}" if media.duration_seconds else None,
        decimal(media.file_length) if media.file_length else None,
    ]
    return Text(" · ".join(filter(None, parts)), style="cyan")
