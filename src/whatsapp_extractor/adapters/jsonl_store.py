from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from whatsapp_extractor.domain import Message

if TYPE_CHECKING:
    from pathlib import Path


class JsonlMessageStore:
    """Append-only JSON Lines file: O(1) save, O(n) load.

    Replacing appends a new line; the last line of an id wins.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    async def save(self, message: Message) -> None:
        await asyncio.to_thread(self._append, message.model_dump_json())

    async def load(self, message_id: str) -> Message | None:
        line = await asyncio.to_thread(self._last_line_of, message_id)
        return Message.model_validate_json(line) if line else None

    def _append(self, line: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as file:
            file.write(line + "\n")

    def _last_line_of(self, message_id: str) -> str | None:
        if not self._path.exists():
            return None
        found = None
        with self._path.open(encoding="utf-8") as file:
            for line in file:
                if json.loads(line)["id"] == message_id:
                    found = line
        return found
