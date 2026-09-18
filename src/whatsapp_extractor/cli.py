"""The executable. Reads configuration through `Settings`; writes it only through `TomlConfig`."""

from __future__ import annotations

import asyncio
import contextlib
import sys
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from . import bootstrap
from .adapters.neonize_accounts import Account, list_accounts
from .adapters.toml_config import GLOBAL, TomlConfig
from .settings import Settings

app = typer.Typer(no_args_is_help=True, add_completion=False)
account_app = typer.Typer(no_args_is_help=True, help="The account `run` uses by default.")
watch_app = typer.Typer(no_args_is_help=True, help="What each account extracts.")
app.add_typer(account_app, name="account")
app.add_typer(watch_app, name="watch")

ConfigOption = Annotated[Path | None, typer.Option("--config", "-c", help="TOML config file.")]
AccountOption = Annotated[str | None, typer.Option("--account", "-a", help="Phone of the account.")]


@app.command()
def run(account: AccountOption = None, config: ConfigOption = None) -> None:
    """Extract messages for one paired account."""
    settings = Settings.load(config, **({"account": account} if account else {}))
    chosen = choose_account(settings)
    bootstrap.configure_logging()
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(bootstrap.run(settings.model_copy(update={"account": chosen.phone})))


@app.command()
def accounts(config: ConfigOption = None) -> None:
    """List the accounts paired in the database."""
    settings = Settings.load(config)
    paired = list_accounts(settings.database)
    if not paired:
        typer.echo("no account paired yet; run `pair`")
        return
    for paired_account in paired:
        marker = "*" if paired_account.phone == settings.account else " "
        typer.echo(f"{marker} {paired_account.phone}  {paired_account.name}")


@app.command()
def pair(config: ConfigOption = None) -> None:
    """Pair one more phone: scan the QR code, wait for the first sync."""
    settings = Settings.load(config)
    bootstrap.configure_logging()
    pairing = bootstrap.Pairing(settings)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(pairing.run())
    if pairing.account is None:
        fail("pairing did not complete")
    TomlConfig(settings.config).add_account(pairing.account.phone)
    typer.echo(f"paired {pairing.account.phone} ({pairing.account.name})")


@app.command()
def migrate(
    account: AccountOption = None,
    *,
    every: Annotated[bool, typer.Option("--all", help="Every paired account.")] = False,
    config: ConfigOption = None,
) -> None:
    """Bring the message schema of an account (or all) to the latest revision."""
    settings = Settings.load(config, **({"account": account} if account else {}))
    bootstrap.configure_logging()
    targets = list_accounts(settings.database) if every else [choose_account(settings)]
    for target in targets:
        asyncio.run(bootstrap.migrate_account(settings, target.phone))
        typer.echo(f"migrated {target.phone}")


@account_app.command("use")
def account_use(phone: str, config: ConfigOption = None) -> None:
    """Make an account the default for `run`."""
    settings = Settings.load(config)
    if not any(paired.phone == phone for paired in list_accounts(settings.database)):
        fail(f"{phone} is not paired; run `pair` first")
    TomlConfig(settings.config).set_account(phone)
    typer.echo(f"default account: {phone}")


SenderFlag = Annotated[bool, typer.Option("--sender", help="A sender instead of a chat.")]
GlobalFlag = Annotated[bool, typer.Option("--global", help="The global watchlist.")]


@watch_app.command("add")
def watch_add(
    entry: str,
    account: AccountOption = None,
    *,
    sender: SenderFlag = False,
    global_: GlobalFlag = False,
    config: ConfigOption = None,
) -> None:
    """Watch a chat (JID or counterpart phone) or, with --sender, a person."""
    settings = Settings.load(config)
    target = watch_target(settings, account, global_=global_)
    TomlConfig(settings.config).watch(entry, senders=sender, account=target)
    typer.echo(f"watching {entry} ({scope_name(target)})")


@watch_app.command("remove")
def watch_remove(
    entry: str,
    account: AccountOption = None,
    *,
    sender: SenderFlag = False,
    global_: GlobalFlag = False,
    config: ConfigOption = None,
) -> None:
    """Stop watching a chat or, with --sender, a person."""
    settings = Settings.load(config)
    target = watch_target(settings, account, global_=global_)
    TomlConfig(settings.config).unwatch(entry, senders=sender, account=target)
    typer.echo(f"no longer watching {entry} ({scope_name(target)})")


@watch_app.command("list")
def watch_list(account: AccountOption = None, config: ConfigOption = None) -> None:
    """Show the watchlist in effect for an account (or the global one)."""
    settings = Settings.load(config)
    phone = account or settings.account
    watchlist = settings.watchlist_for(phone) if phone else settings.watchlist
    typer.echo(f"scope: {scope_name(phone)}")
    for chat in sorted(watchlist.chats):
        typer.echo(f"chat    {chat}")
    for person in sorted(watchlist.senders):
        typer.echo(f"sender  {person}")
    if not watchlist.chats and not watchlist.senders:
        typer.echo("(empty: everything is extracted)")


def choose_account(settings: Settings) -> Account:
    """The configured account, the only paired one, or an interactive choice."""
    paired = list_accounts(settings.database)
    if settings.account:
        chosen = next((a for a in paired if a.phone == settings.account), None)
        return chosen or fail(f"{settings.account} is not paired; run `pair` or `accounts`")
    if not paired:
        fail("no account paired yet; run `pair`")
    if len(paired) == 1:
        return paired[0]
    if not sys.stdin.isatty():
        fail("several accounts are paired; pass --account: " + ", ".join(a.phone for a in paired))
    for index, option in enumerate(paired, start=1):
        typer.echo(f"{index}. {option.phone}  {option.name}")
    choice: int = typer.prompt("account", type=int)
    if not 1 <= choice <= len(paired):
        fail(f"choose between 1 and {len(paired)}")
    return paired[choice - 1]


def watch_target(settings: Settings, account: str | None, *, global_: bool) -> str | None:
    if global_:
        return GLOBAL
    target = account or settings.account
    if target is None:
        fail("pass --account, set a default with `account use`, or use --global")
    return target


def scope_name(account: str | None) -> str:
    return "global" if account is GLOBAL else f"account {account}"


def fail(message: str) -> NoReturn:
    typer.echo(f"error: {message}", err=True)
    raise typer.Exit(code=1)
