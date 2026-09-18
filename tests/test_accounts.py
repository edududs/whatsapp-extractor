from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
from neonize.proto.Neonize_pb2 import JID, Device

from whatsapp_extractor.adapters.neonize_accounts import account_of
from whatsapp_extractor.testing import phones


@given(phone=phones(), device=st.integers(min_value=0, max_value=99), name=st.text(max_size=20))
def test_the_phone_is_the_user_part_without_the_device_index(
    phone: str, device: int, name: str
) -> None:
    user = f"{phone}:{device}" if device else phone
    raw = Device(JID=JID(User=user, Server="s.whatsapp.net"), PushName=name)
    account = account_of(raw)
    assert account.phone == phone
    assert account.name == name
    assert account.device.User == user  # opening the client needs the full address


def test_business_name_is_the_fallback_name() -> None:
    raw = Device(JID=JID(User="5511900000001", Server="s.whatsapp.net"), BussinessName="Shop")
    assert account_of(raw).name == "Shop"
