from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from whatsapp_extractor.domain import MessageExtracted

log = logging.getLogger(__name__)


async def log_message_extracted(event: MessageExtracted) -> None:
    log.info("extracted %s", event.message.model_dump_json())
