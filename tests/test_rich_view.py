from __future__ import annotations

import io
from typing import TYPE_CHECKING

from hypothesis import given
from rich.console import Console

from whatsapp_extractor import Media, MediaKind, MessageExtracted
from whatsapp_extractor.adapters.rich_view import message_view, render_json, render_panel
from whatsapp_extractor.testing import make_message, messages

if TYPE_CHECKING:
    from whatsapp_extractor import Message
    from whatsapp_extractor.adapters.rich_view import Renderer


async def shown(message: Message, render: Renderer = render_panel) -> str:
    output = io.StringIO()
    console = Console(file=output, width=120, color_system=None)
    await message_view(console, render)(MessageExtracted(message=message))
    return output.getvalue()


async def test_panel_shows_where_who_and_what() -> None:
    output = await shown(make_message(text="Bom dia"))
    assert "GROUP 120363000000000001@g.us" in output
    assert "Alice 5511900000001" in output
    assert "Bom dia" in output
    assert "text · msg-1" in output


async def test_message_text_is_never_interpreted_as_markup() -> None:
    assert "[red]not markup[/red]" in await shown(make_message(text="[red]not markup[/red]"))


async def test_panel_summarises_media_in_one_line() -> None:
    voice_note = Media(
        kind=MediaKind.AUDIO,
        mimetype="audio/ogg",
        duration_seconds=82,
        file_length=202537,
        is_voice_note=True,
    )
    message = make_message(text="")
    message = message.model_copy(
        update={"content": message.content.model_copy(update={"media": voice_note})}
    )
    assert "voice note · audio/ogg · 1:22 · 202.5 kB" in await shown(message)


async def test_panel_says_when_there_is_no_content() -> None:
    assert "(no content)" in await shown(make_message(text=""))


@given(message=messages())
def test_every_message_renders_in_both_views_and_shows_its_id(message: Message) -> None:
    for render in (render_panel, render_json):
        output = io.StringIO()
        Console(file=output, width=400, color_system=None).print(render(message))
        assert message.id in output.getvalue()


async def test_json_view_shows_the_whole_mapped_message() -> None:
    output = await shown(make_message(), render_json)
    assert '"counterpart_phone": null' in output
    assert '"pushname": "Alice"' in output
