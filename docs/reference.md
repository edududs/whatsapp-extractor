# Reference

The complete reference for configuration, the CLI, the data model, the ports and the storage
layout. The [README](../README.md) covers the overview and the quick start;
[decisions.md](decisions.md) records why things are the way they are.

## Configuration

Configuration lives in `extractor.toml` in the current directory, or the path selected by
`EXTRACTOR_CONFIG` or `--config/-c`. The CLI writes changes through tomlkit, preserving comments.
Reading settings and running extraction never rewrite the file.

Precedence, highest first: explicit CLI arguments or `Settings.load` overrides, environment
variables, `.env`, TOML, defaults. Use TOML for normal options and environment settings for secrets
or deployment overrides.

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

A message is accepted when its chat **or** sender matches. Two empty arrays accept everything,
including direct chats. Creating an account watchlist does not copy or merge the global list.

| Environment setting | Default | Meaning |
| --- | --- | --- |
| `EXTRACTOR_DATABASE` | `session.db` | SQLite session file or PostgreSQL DSN. Contains WhatsApp credentials: never commit or share it. |
| `EXTRACTOR_MESSAGES_DATABASE` | Unset | Separate SQLite file or PostgreSQL DSN for the `wa_<phone>` message schemas. Blank or absent means the session database. |
| `EXTRACTOR_ACCOUNT` | Unset | Default phone override for unattended services. A blank assignment clears the TOML default; omit the variable to use the TOML account. |
| `EXTRACTOR_CONFIG` | `extractor.toml` | Configuration file path, accepted in the environment or `.env`. CLI edits use this same resolved path. |

Local `extractor.toml`, `.env`, databases and JSON Lines output are ignored by Git. The
configuration may contain private chat identifiers.

## CLI

Each command accepts `--config/-c FILE`. Account options use `--account/-a PHONE`. The module
entry point is the same CLI: `python -m whatsapp_extractor run`.

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

For `run`, `groups` and `migrate`, an explicit or configured phone must be paired. Without one,
the CLI selects the only paired account. If several exist, an interactive terminal prompts for a
numbered choice; without a terminal it exits with code 1 and lists the available phones. This
choice is not saved.

Watch edits without `--account` use the configured default. Without a default, supply `--account`
or `--global`. Unlike edits, `watch list` can show the global list without a configured account.

During pairing, neonize prints a QR code. Scan it from WhatsApp's **Linked devices** screen and
wait for the initial synchronization to finish. The command records the paired phone in the TOML
configuration; it does not make it the default. For an existing pairing, skip `pair` and use
`accounts` to find its phone.

`run` logs the effective watchlist when it starts, so an empty screen means no matching message
arrived rather than a dead connection.

## Embedding

`whatsapp_extractor.bootstrap.run(settings, *handlers, source=None, accepts=None, writer=None)`
extracts one account and requires `settings.account`; otherwise it raises `AccountRequiredError`.
An unpaired phone raises `AccountNotPairedError`.

```python
import asyncio
from pathlib import Path

from whatsapp_extractor import MessageExtracted
from whatsapp_extractor.bootstrap import run
from whatsapp_extractor.settings import Settings


async def show_id(event: MessageExtracted) -> None:
    print(event.message.id, event.message.chat.jid.value)


settings = Settings.load(Path("extractor.toml"), account="5511900000001")
asyncio.run(run(settings, show_id))
```

The default source opens that account's device; the default filter is
`settings.watchlist_for(account).matches`. The SQL writer migrates and opens the account's schema;
JSON Lines uses the account-specific path; the memory store is process-local. Handlers run after
the configured view, in order, on the same event loop.

`run` does not configure logging. The CLI calls `configure_logging()`; an embedding application
keeps its own logging configuration. neonize calls `logging.basicConfig` when imported, which is a
no-op once the root logger has a handler.

For manual composition, pass a source, a filter, a writer and an event bus to `extract`:

```python
from whatsapp_extractor import EventBus, MessageExtracted, MessageSource, Watchlist, extract
from whatsapp_extractor.adapters.memory_store import InMemoryMessageStore


async def show_id(event: MessageExtracted) -> None:
    print(event.message.id)


async def consume(source: MessageSource) -> None:
    bus = EventBus()
    bus.subscribe(MessageExtracted, show_id)
    await extract(source, Watchlist().matches, InMemoryMessageStore(), bus)
```

The bus awaits handlers in subscription order. Subscriptions to a base event type also receive its
subtypes. Callers manage the lifecycle and account isolation of adapters they supply; the domain,
the ports, `extract` and the bus know nothing about accounts.

## Data model

Models are frozen pydantic models exported from the package root.

| Model | Fields |
| --- | --- |
| `Message` | id, timestamp, kind, from_me, chat, sender, recipient, content, is_ephemeral, is_view_once, is_edit |
| `Chat` | jid, kind, counterpart_phone, name |
| `Sender` | jid, lid, phone, pushname |
| `Content` | text, media |
| `Media` | kind, mimetype, caption, duration_seconds, width, height, file_length, file_name, is_voice_note |

Direct-chat names come from the contact store: the saved full name takes precedence over the
business name and the pushname. Group names are not populated on messages; the `groups` command
resolves them. Unknown `MessageKind` values become `UNKNOWN` instead of rejecting the message.
`Media` holds metadata; the extractor does not download files.

## Ports

| Port | Interface |
| --- | --- |
| `MessageSource` | `messages() -> AsyncIterator[Message]` |
| `MessageFilter` | `Callable[[Message], bool]` |
| `MessageWriter` | `async save(message: Message) -> None` |
| `MessageStore` | `MessageWriter` plus `async load(message_id: str) -> Message \| None` |
| `EventHandler` | Async callable receiving an event and returning `None`. |
| `EventPublisher` | `async publish(event: DomainEvent) -> None` |

Source, writer, store and publisher are structural protocols; implementations need not inherit
them. Filters and handlers are callable type aliases.

Persistence belongs in a writer or a store. Other reactions, such as webhooks, terminal
interfaces or classifiers, belong in bus handlers. A writer must create or replace by message id;
a store must return `None` for a missing id.

```python
from whatsapp_extractor import Message, MessageStore


class ForwardingWriter:
    def __init__(self, target: MessageStore) -> None:
        self.target = target

    async def save(self, message: Message) -> None:
        await self.target.save(message)
```

Bundled stores: `InMemoryMessageStore`, `JsonlMessageStore` and `SqlMessageStore`. JSON Lines
appends records and the last record for an id wins. The SQL store keeps the complete JSON payload
alongside indexed `chat_jid` and `timestamp` columns.

## Failure policy

- Writer errors propagate and stop the extraction; no event is published for a failed save.
- Handler exceptions are logged and isolated so later handlers still run.
- Source mapping validation errors are logged and the event is skipped.
- A full input buffer drops new messages and logs the drop.
- Events carrying only a `senderKeyDistributionMessage` are ignored: whatsmeow emits one event per
  encrypted node, and the key-distribution node is not a message.
- Connection errors propagate after buffered messages have been consumed.

## Test kit

Install the `testing` extra to use `whatsapp_extractor.testing`. It exports Hypothesis strategies
(`messages()`, `jids()`, `chats()`, `senders()`, `media()`, `watchlists()`), `make_message()` and
`MessageStoreContract`.

Subclass the contract in a pytest module and provide a fresh, empty store for every example:

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

The contract checks missing ids, round trips, replacement by id and independence between ids.

## Accounts and storage

An account is one paired phone. neonize keeps every pairing in the session database;
`list_accounts(database)` returns each phone, name and device address. One run extracts one
account. To extract several accounts at once, run separate processes with different `--account`
values. Never run the same phone in two processes: WhatsApp disconnects one of them.

Each SQL account owns `wa_<phone>`:

- **PostgreSQL:** a schema in the same database as the `whatsmeow_*` tables, or in the database
  named by `EXTRACTOR_MESSAGES_DATABASE`.
- **SQLite:** an attached `wa_<phone>.db` file next to the session database. The session file keeps
  pairing and contact data.

`engine_for(database, schema)` uses SQLAlchemy's `schema_translate_map` for both backends.
PostgreSQL DSNs beginning with `postgres://` or `postgresql://` become `postgresql+asyncpg` URLs
(install the `postgres` extra). SQLite uses `sqlite+aiosqlite`, a 30-second lock timeout and
`ATTACH DATABASE` on every connection.

`EXTRACTOR_MESSAGES_DATABASE` keeps the message schemas apart from the session. The typical layout
is a local SQLite session file and a PostgreSQL server for messages. This matters on hosted
PostgreSQL services that expose the `public` schema through an HTTP API: whatsmeow creates its
credential tables there, while the `wa_<phone>` schemas are not exposed by default.

`Message` has no account field: the account is process context and storage provides the
namespace. Two accounts may store different messages with the same id.

The `whatsmeow_*` tables hold keys, sessions, contacts and application state, not a message
archive. Extracted messages go to the selected account store only.

### Reading messages from another program

Consumers read the table with their own cursor; the indexes on `chat_jid` and `timestamp` exist
for this query:

```sql
SELECT id, payload
FROM wa_5511900000001.messages
WHERE chat_jid = '120363000000000001@g.us' AND timestamp > :last_seen
ORDER BY timestamp
```

`payload` is the JSON of the `Message` model; `Message.model_validate_json` rebuilds it.

## Migrations

Alembic revisions are packaged under `whatsapp_extractor/migrations`. Revision 0001 creates the
`messages` table and its chat and timestamp indexes. `migrate(engine, schema)` creates the
PostgreSQL schema when needed and upgrades the account to the current revision; each account has
its own `alembic_version` table.

The bundled SQL writer applies migrations when `run` starts. They can also be run explicitly:

```sh
uv run whatsapp-extractor migrate --account 5511900000001
uv run whatsapp-extractor migrate --all
```

## Logging

Only the CLI calls `configure_logging()`. It uses `force=True` because neonize calls `basicConfig`
during import, and it quiets Alembic to `WARNING`. Package modules log through
`logging.getLogger(__name__)`; embedding applications configure their own logging.
