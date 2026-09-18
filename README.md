# whatsapp-extractor

A reusable WhatsApp message extractor with a hexagonal architecture. It selects messages from watched chats or senders, saves each accepted message, then publishes a MessageExtracted event to an in-process asyncio event bus.

    MessageSource → MessageFilter → MessageWriter → EventBus → handlers

The domain is specific to WhatsApp: Jid, ChatKind and related models describe WhatsApp addresses and messages. Sources for unrelated platforms do not fit this domain.

## Requirements and installation

Python 3.13 or later is required for asyncio.Queue.shutdown. Development uses uv. The package is not published on PyPI; install the tagged release from Git:

```sh
uv add "whatsapp-extractor[rich] @ git+https://github.com/edududs/whatsapp-extractor@v0.1.0"
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
uv run whatsapp-extractor
```

On PowerShell, use `Copy-Item .env.example .env`. Edit the configuration before starting. The module entry point is `python -m whatsapp_extractor`.

On the first connection, neonize prints a QR code in the terminal. Scan it from WhatsApp's **Linked devices** screen. The session database preserves the pairing for subsequent runs.

The example configuration contains sample watchlist entries. Set both lists to `[]` to receive all messages and discover chat JIDs, then configure the chats or senders to watch.

## Configuration

Settings read `EXTRACTOR_*` environment variables and `.env`. Environment variables take precedence over the file.

| Variable | Default | Meaning |
| --- | --- | --- |
| `EXTRACTOR_DATABASE` | `session.db` | Shared SQLite file or `postgres://...` DSN for neonize's pairing/contact data and the extractor's SQL messages table. Contains WhatsApp credentials: never commit or share it. |
| `EXTRACTOR_WATCHLIST__CHATS` | `[]` | JSON array of chat JIDs, such as `123@g.us`, or the other participant's phone number for direct chats. |
| `EXTRACTOR_WATCHLIST__SENDERS` | `[]` | JSON array of sender JIDs, phone numbers or LIDs. |
| `EXTRACTOR_STORE` | `sql` | Persistence: `memory`, `jsonl` or `sql`. |
| `EXTRACTOR_JSONL_PATH` | `messages.jsonl` | Output path when the store is `jsonl`. |
| `EXTRACTOR_BUFFER_SIZE` | `10000` | Buffered messages while consumption lags. New arrivals beyond the limit are dropped and logged. |
| `EXTRACTOR_VIEW` | `panel` | Output: `panel`, `json` or `log`. Panel and JSON require the rich extra; both fall back to log when it is unavailable. |

A message is accepted when its chat **or** sender matches. Two empty lists accept everything.

## Use in another project

`whatsapp_extractor.bootstrap.run(settings, *handlers, source=None, accepts=None, writer=None)` composes the bundled adapters. Omitted pieces are selected from Settings. Additional handlers run after the configured view.

```python
import asyncio

from whatsapp_extractor import MessageExtracted, Watchlist
from whatsapp_extractor.bootstrap import run
from whatsapp_extractor.settings import Settings


async def show_id(event: MessageExtracted) -> None:
    print(event.message.id, event.message.chat.jid.value)


settings = Settings(
    watchlist=Watchlist(chats=frozenset({"123@g.us"})),
)
asyncio.run(run(settings, show_id))
```

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

The bus awaits handlers in subscription order. Subscriptions to a base event type also receive its subtypes. Callers manage the lifecycle of adapters they supply.

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

## Shared database

EXTRACTOR_DATABASE is passed to neonize as its client name. A PostgreSQL DSN selects its PostgreSQL backend; otherwise it uses a SQLite file. Use `postgres://...` or `postgresql://...` for compatibility with engine_for().

The extractor's engine_for() derives a `postgresql+asyncpg` SQLAlchemy URL for those DSNs or a `sqlite+aiosqlite` URL for a file. SQLite uses a 30-second lock timeout because neonize writes to the same database. Install the postgres extra for PostgreSQL.

The whatsmeow_* tables hold keys, sessions, contacts and application state. Whatsmeow does not archive messages. With the SQL store selected, this package creates and writes its own messages table in the shared database. With memory or JSON Lines selected, neonize still uses the configured session database, while extracted messages go to the selected store.

## Logging

Only the executable calls configure_logging(). It uses force=True because neonize calls basicConfig during import. Package modules emit records with logging.getLogger(__name__); applications using the library configure their own logging.

## Development

```sh
uv sync --all-extras
uv run poe fix
uv run poe check
```

The fix task formats, applies lint fixes, runs strict type checking and executes the tests. The check task runs the same gate without rewriting source files: Ruff formatting checks, Ruff with all lint rules selected and documented exceptions, strict Pyright, and pytest with Hypothesis.

CI runs the check task on Ubuntu and Windows. tests/test_architecture.py enforces the domain/application import boundaries: standard library, Pydantic, the current layer and permitted lower layers.

## Versioning

Releases follow Semantic Versioning 2.0.0 and are recorded in [CHANGELOG.md](CHANGELOG.md). Version 0.1.0 is the initial alpha release; the public API may change during 0.x development.

## Unofficial API

This project uses neonize/whatsmeow, an unofficial WhatsApp API, and is not affiliated with Meta or WhatsApp. Use violates WhatsApp's terms of service and may result in an account ban. Use it at your own risk.

## License

See [LICENSE](LICENSE).
