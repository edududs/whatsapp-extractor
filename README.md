# whatsapp-extractor

A reusable WhatsApp message extractor with a hexagonal architecture. It selects messages from watched chats or senders, saves each accepted message, then publishes a MessageExtracted event to an in-process asyncio event bus.

    MessageSource → MessageFilter → MessageWriter → EventBus → handlers

The domain is specific to WhatsApp: Jid, ChatKind and related models describe WhatsApp addresses and messages. Sources for unrelated platforms do not fit this domain.

## Requirements and installation

Python 3.13 or later is required for asyncio.Queue.shutdown. Development uses uv. The package is not published on PyPI; install the tagged release from Git:

```sh
uv add "whatsapp-extractor[rich] @ git+https://github.com/edududs/whatsapp-extractor@v0.2.0"
```

Optional extras:

- **rich**: terminal panels and JSON output.
- **testing**: Hypothesis strategies, a message factory and a reusable store contract.
- **postgres**: the asyncpg driver for PostgreSQL.

## Standalone use

From a checkout:

```sh
uv sync --all-extras
cp .env.example .env
uv run whatsapp-extractor pair
uv run whatsapp-extractor account use 5511900000001
uv run whatsapp-extractor groups
uv run whatsapp-extractor watch add 120363000000000001@g.us
uv run whatsapp-extractor run
```

On PowerShell, use `Copy-Item .env.example .env`. Replace the sample phone and chat JID with your own. Review the environment settings before starting. Remove the EXTRACTOR_ACCOUNT line from the copied .env to use the default saved by account use; keep it only when deliberately overriding that default. The module entry point is the same CLI: `python -m whatsapp_extractor run`. Invoking the executable without a command displays help.

During pairing, neonize prints a QR code. Scan it from WhatsApp's **Linked devices** screen and wait for initial synchronization to finish. The command records the paired phone in the TOML configuration; it does not make it the default. Ctrl+C after the phone has linked also lets the command record the account.

For an existing pairing, skip `pair` and use `accounts` to find its phone. The configuration file need not exist: commands that edit it create it. See [extractor.example.toml](extractor.example.toml) for the full structure.

`groups` connects briefly as the selected account, prints the address, name and size of every group it belongs to, and disconnects. Copy the address of a group into `watch add`. With both watchlist arrays empty, every message is accepted, which also reveals the addresses of direct chats and other senders.


## Configuration

Configuration lives in `extractor.toml` in the current directory, or the path selected by `EXTRACTOR_CONFIG` or `--config/-c`. The CLI writes changes through tomlkit, preserving comments. Reading settings and running extraction do not rewrite the file.

Precedence, highest first: explicit CLI arguments or Settings.load overrides, environment variables, `.env`, TOML, defaults. Use TOML for normal options and environment settings for secrets or deployment overrides.

```toml
account = "5511900000001"
store = "sql"
view = "panel"
buffer_size = 10000
jsonl_path = "messages_{account}.jsonl"

[watchlist]
chats = []
senders = []

[accounts."5511900000001".watchlist]
chats = ["120363000000000001@g.us"]
senders = ["5511900000002"]
```

| TOML key | Default | Meaning |
| --- | --- | --- |
| `account` | Unset | Default paired phone, 5–15 digits, including the country code. |
| `store` | `"sql"` | Persistence: `"memory"`, `"jsonl"` or `"sql"`. |
| `view` | `"panel"` | Output: `"panel"`, `"json"` or `"log"`. Panel and JSON fall back to logging if rich is unavailable. |
| `buffer_size` | `10000` | Buffered messages; new arrivals beyond the limit are dropped and logged. |
| `jsonl_path` | `"messages_{account}.jsonl"` | JSON Lines path template; `{account}` is replaced by the selected phone. Keep the placeholder when sharing configuration across accounts. |
| `watchlist.chats` | `[]` | Chat JIDs or the other participant's phone number for direct chats. |
| `watchlist.senders` | `[]` | Sender JIDs, phone numbers or LIDs. |
| `accounts."<phone>".watchlist` | Absent | Replaces the global watchlist for this account, including when its arrays are empty. |

A message is accepted when its chat **or** sender matches. Two empty arrays accept everything. Creating an account watchlist does not copy or merge the global list.

| Environment setting | Default | Meaning |
| --- | --- | --- |
| `EXTRACTOR_DATABASE` | `session.db` | SQLite session file or PostgreSQL DSN. Contains WhatsApp credentials: never commit or share it. |
| `EXTRACTOR_MESSAGES_DATABASE` | Unset | Separate SQLite file or PostgreSQL DSN for the `wa_<phone>` message schemas. Blank or absent means the session database. |
| `EXTRACTOR_ACCOUNT` | Unset | Default phone override for unattended services. A blank assignment clears the TOML default; omit the variable to use the TOML account. |
| `EXTRACTOR_CONFIG` | `extractor.toml` | Configuration file path, accepted in the environment or .env. CLI edits use this same resolved path. |

Local `extractor.toml`, `.env`, databases and JSON Lines output are ignored by Git. The configuration may contain private chat identifiers.

## CLI reference

Each command accepts `--config/-c FILE`. Account options use `--account/-a PHONE`.

| Command | Effect | Writes TOML? |
| --- | --- | --- |
| `run [--account PHONE]` | Extract messages for one paired account. | No |
| `accounts` | List paired phones and names; `*` marks the configured default. | No |
| `groups [--account PHONE]` | Connect briefly and list the groups the account belongs to: address, name and member count. | No |
| `pair` | Pair another phone and record its account after linking. | Yes |
| `migrate [--account PHONE]` | Upgrade one account's message schema. | No |
| `migrate --all` | Upgrade all paired accounts. | No |
| `account use PHONE` | Set the default; reject an unpaired phone. | Yes |
| `watch add ENTRY [--sender] [--account PHONE \| --global]` | Add a chat or sender to the selected scope. | Yes |
| `watch remove ENTRY [--sender] [--account PHONE \| --global]` | Remove a chat or sender from the selected scope. | Yes |
| `watch list [--account PHONE]` | Show the effective account watchlist, or the global list when no account is configured. | No |

For `run`, `groups` and `migrate`, an explicit or configured phone must be paired. Without one, the CLI selects the only paired account. If several exist, an interactive terminal prompts for a numbered choice; without a terminal it exits with code 1 and lists the available phones. This choice is not saved.

Watch edits without `--account` use the configured default. Without a default, supply `--account` or `--global`. Unlike edits, `watch list` can show the global list without a configured account.


## Use in another project

`whatsapp_extractor.bootstrap.run(settings, *handlers, source=None, accepts=None, writer=None)` extracts one account and requires `settings.account`; otherwise it raises AccountRequiredError. Load configuration with Settings.load():

```python
import asyncio
from pathlib import Path

from whatsapp_extractor import MessageExtracted
from whatsapp_extractor.bootstrap import run
from whatsapp_extractor.settings import Settings


async def show_id(event: MessageExtracted) -> None:
    print(event.message.id, event.message.chat.jid.value)


settings = Settings.load(
    Path("extractor.toml"),
    account="5511900000001",
)
asyncio.run(run(settings, show_id))
```

Replace the phone with an account paired in the configured database. The default source opens that account's device; the default filter is settings.watchlist_for(account).matches. The SQL writer migrates and opens the account's schema. JSON Lines uses the account-specific path, and the memory store is process-local. Additional handlers run after the configured view.

For manual composition, pass your source, filter, writer and event bus directly to extract:

```python
from whatsapp_extractor import (
    EventBus,
    MessageExtracted,
    MessageSource,
    Watchlist,
    extract,
)
from whatsapp_extractor.adapters.memory_store import InMemoryMessageStore


async def show_id(event: MessageExtracted) -> None:
    print(event.message.id)


async def consume(source: MessageSource) -> None:
    bus = EventBus()
    bus.subscribe(MessageExtracted, show_id)
    await extract(source, Watchlist().matches, InMemoryMessageStore(), bus)
```

The bus awaits handlers in subscription order. Subscriptions to a base event type also receive its subtypes. Callers manage the lifecycle and account isolation of adapters they supply. The domain, ports, extract function and bus do not select accounts.


## Data model

Models are frozen Pydantic models, exported from the package root:

| Model | Fields |
| --- | --- |
| Message | id, timestamp, kind, from_me, chat, sender, recipient, content, is_ephemeral, is_view_once, is_edit |
| Chat | jid, kind, counterpart_phone, name |
| Sender | jid, lid, phone, pushname |
| Content | text, media |
| Media | kind, mimetype, caption, duration_seconds, width, height, file_length, file_name, is_voice_note |

Direct-chat names come from the contact store: the saved full name takes precedence over the business name and pushname. Group names are not populated. Unknown MessageKind values become UNKNOWN instead of rejecting the message. Media contains metadata; the extractor does not download media files.

## Write an adapter

The package root exports these ports:

| Port | Interface |
| --- | --- |
| MessageSource | `messages() -> AsyncIterator[Message]` |
| MessageFilter | `Callable[[Message], bool]` |
| MessageWriter | `async save(message: Message) -> None` |
| MessageStore | MessageWriter plus `async load(message_id: str) -> Message \| None` |
| EventHandler | Async callable receiving an event and returning None. |
| EventPublisher | `async publish(event: DomainEvent) -> None` |

Source, writer, store and publisher are structural Protocols; implementations need not inherit them. Filters and handlers are callable type aliases.

Persistence belongs in a writer or store. Other reactions, such as webhooks, terminal interfaces or classifiers, belong in bus handlers. A writer must create or replace by message ID; a store must return None for a missing ID. For example, this writer forwards messages to an existing store:

```python
from whatsapp_extractor import Message, MessageStore


class ForwardingWriter:
    def __init__(self, target: MessageStore) -> None:
        self.target = target

    async def save(self, message: Message) -> None:
        await self.target.save(message)
```

Bundled stores are InMemoryMessageStore, JsonlMessageStore and SqlMessageStore. JSON Lines appends records; the last record for an ID wins. The SQL store keeps the complete JSON payload alongside indexed chat and timestamp projections.

## Failure policy

- Writer errors propagate and stop extraction; no event is published for a failed save.
- Handler exceptions are logged and isolated so later handlers can still run.
- Source mapping validation errors are logged and skipped.
- A full input buffer drops new messages and logs the drop.
- Events carrying only senderKeyDistributionMessage are ignored. These are key-distribution blocks, not an additional message; whatsmeow can emit separate events for encrypted blocks in groups and status updates.
- Connection errors propagate after buffered messages have been consumed.

## Test kit

Install the testing extra to use `whatsapp_extractor.testing`. It exports Hypothesis strategies including messages(), jids(), chats(), senders(), media() and watchlists(), plus make_message() and MessageStoreContract.

Subclass the contract in a pytest test module and provide a fresh, empty store for every example. This runnable example uses the bundled memory store; replace it with your adapter and release its resources on context exit:

```python
import contextlib
from collections.abc import AsyncIterator

from whatsapp_extractor import MessageStore
from whatsapp_extractor.adapters.memory_store import InMemoryMessageStore
from whatsapp_extractor.testing import MessageStoreContract


class TestMemoryStore(MessageStoreContract):
    @contextlib.asynccontextmanager
    async def open_store(self) -> AsyncIterator[MessageStore]:
        yield InMemoryMessageStore()
```

The contract checks missing IDs, round trips, replacement by ID and independence between different IDs.

## Accounts and storage isolation

An account is one paired phone. Neonize keeps multiple pairings in the session database; list_accounts(database) returns each phone, name and device address. One run extracts one account. To extract several accounts concurrently, use separate processes with different `--account` values. Do not run the same phone in two processes: WhatsApp disconnects one of them.

Each SQL account owns `wa_<phone>`:

- **PostgreSQL:** a separate schema in the same database as the whatsmeow_* tables.
- **SQLite:** an attached `wa_<phone>.db` file next to the session database. The session file retains pairing and contact data.

engine_for(database, schema) uses SQLAlchemy's schema_translate_map for both backends. PostgreSQL DSNs beginning with `postgres://` or `postgresql://` become `postgresql+asyncpg` URLs. SQLite uses `sqlite+aiosqlite`, a 30-second lock timeout and ATTACH DATABASE for each connection. Install the postgres extra for PostgreSQL.

Set `EXTRACTOR_MESSAGES_DATABASE` to keep the message schemas in a different database from the session. A typical layout keeps the session in a local SQLite file and sends messages to a PostgreSQL server. This matters on hosted PostgreSQL services that expose the `public` schema through an HTTP API: whatsmeow creates its session tables there, while the `wa_<phone>` schemas are not exposed by default.

Message has no account field: the account is process context, and storage provides the namespace. Two accounts may store different messages with the same ID. Separate SQLite session files in the same directory still use the same account filename for a given phone; use separate directories when independent stores are required.

The whatsmeow_* tables store keys, sessions, contacts and application state, not a message archive. This package writes extracted messages to the selected account store.

## Migrations

Alembic revisions are packaged under `whatsapp_extractor/migrations`. Revision 0001 creates the messages table and its chat/timestamp indexes. migrate(engine, schema) creates the PostgreSQL schema when needed and upgrades the account to the current revision. Each account has its own alembic_version table.

The bundled SQL writer applies migrations when run starts. They can also be run explicitly:

```sh
uv run whatsapp-extractor migrate --account 5511900000001
uv run whatsapp-extractor migrate --all
```

An unqualified messages table from a pre-release checkout is not migrated or read by the account stores. It remains in place; preserve any needed data before removing that obsolete table.


## Logging

Only the executable calls configure_logging(). It uses force=True because neonize calls basicConfig during import. Package modules emit records with logging.getLogger(__name__); applications using the library configure their own logging.

## Development

```sh
uv sync --all-extras
uv run poe fix
uv run poe check
```

The fix task formats, applies lint fixes, runs strict type checking and executes the tests. The check task runs the same gate without rewriting source files: Ruff formatting checks, Ruff with all lint rules selected and documented exceptions, strict Pyright, and pytest with Hypothesis.

Tests cover schema isolation, configuration precedence, TOML edits and CLI commands with simulated paired accounts. Pairing and the account-aware run have not yet been validated against live WhatsApp.

CI runs the check task on Ubuntu and Windows. tests/test_architecture.py enforces the domain/application import boundaries: standard library, Pydantic, the current layer and permitted lower layers.

## Versioning

Releases follow Semantic Versioning 2.0.0 and are recorded in [CHANGELOG.md](CHANGELOG.md). Version 0.1.0 was the initial alpha release; the public API may change during 0.x development.

## Unofficial API

This project uses neonize/whatsmeow, an unofficial WhatsApp API, and is not affiliated with Meta or WhatsApp. Use violates WhatsApp's terms of service and may result in an account ban. Use it at your own risk.

## License

See [LICENSE](LICENSE).
