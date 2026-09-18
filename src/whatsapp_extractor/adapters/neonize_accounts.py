"""The accounts paired in a neonize database."""

from __future__ import annotations

from typing import TYPE_CHECKING

from neonize.aioze.client import ClientFactory
from neonize.proto.Neonize_pb2 import JID
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from neonize.proto.Neonize_pb2 import Device


class Account(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    phone: str
    name: str
    device: JID
    """The device address whatsmeow stores (`phone:device@server`), needed to open the client."""


def account_of(device: Device) -> Account:
    # whatsmeow keeps the device index inside the user part: "5511900000001:62".
    phone = device.JID.User.split(":", 1)[0]
    return Account(phone=phone, name=device.PushName or device.BussinessName, device=device.JID)


def list_accounts(database: str) -> list[Account]:
    """Every account paired in `database` (a SQLite file or a postgres DSN)."""
    return [account_of(device) for device in ClientFactory.get_all_devices_from_db(database)]


def find_account(database: str, phone: str) -> Account | None:
    return next((account for account in list_accounts(database) if account.phone == phone), None)
