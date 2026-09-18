from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import model_validator

from .base import FrozenModel

LID_SERVER = "lid"
PHONE_SERVER = "s.whatsapp.net"
GROUP_SERVER = "g.us"
NEWSLETTER_SERVER = "newsletter"
BROADCAST_SERVER = "broadcast"
STATUS_USER = "status"


class Jid(FrozenModel):
    """WhatsApp address: `user@server`, or just `server`."""

    user: str = ""
    server: str = ""

    @model_validator(mode="after")
    def must_be_populated(self) -> Self:
        if not self.user and not self.server:
            msg = "JID must have user or server"
            raise ValueError(msg)
        return self

    @property
    def value(self) -> str:
        return f"{self.user}@{self.server}" if self.user else self.server

    @property
    def phone(self) -> str | None:
        return self._user_on(PHONE_SERVER)

    @property
    def lid(self) -> str | None:
        return self._user_on(LID_SERVER)

    def _user_on(self, server: str) -> str | None:
        return self.user if self.user and self.server == server else None


class ChatKind(StrEnum):
    DIRECT = "direct"
    GROUP = "group"
    STATUS = "status"
    BROADCAST = "broadcast"
    NEWSLETTER = "newsletter"
    UNKNOWN = "unknown"

    @classmethod
    def of(cls, jid: Jid) -> ChatKind:
        if jid.user == STATUS_USER and jid.server == BROADCAST_SERVER:
            return cls.STATUS
        return _KIND_BY_SERVER.get(jid.server, cls.UNKNOWN)


_KIND_BY_SERVER = {
    LID_SERVER: ChatKind.DIRECT,
    PHONE_SERVER: ChatKind.DIRECT,
    GROUP_SERVER: ChatKind.GROUP,
    NEWSLETTER_SERVER: ChatKind.NEWSLETTER,
    BROADCAST_SERVER: ChatKind.BROADCAST,
}
