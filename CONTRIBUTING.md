# Contributing

## Setup

```sh
uv sync --all-extras
uv run poe fix
```

`fix` formats, applies lint fixes, type-checks and runs the tests with coverage. `check` is the same
gate without rewriting files; CI runs it on Ubuntu and Windows, on Python 3.13 and 3.14.

## What the gate enforces

- **Ruff** with every rule selected. Each ignore in `pyproject.toml` says why it exists.
- **Pyright** in strict mode over `src` and `tests`.
- **Tests** with a coverage floor. `tests/test_architecture.py` fails when `domain` or
  `application` import anything beyond the standard library, pydantic and the layers beneath them.
- **Hypothesis** for the domain rules and the store contract; new adapters should subclass
  `MessageStoreContract` from `whatsapp_extractor.testing`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org): `feat`, `fix`, `refactor`, `docs`,
`test`, `ci`, `chore`, with an optional scope such as `cli`, `config`, `adapters` or `storage`.
The changelog and the release notes are generated from these messages, so the subject line should
describe the change for a reader of the changelog. Do not add trailers.

Never commit `.env`, `session.db`, `wa_*.db` or `extractor.toml`: the session database holds
WhatsApp credentials and the configuration may name private chats.

## Changing the public contract

The public contract is what the package root exports (models, ports, `extract`, `EventBus`) plus
`bootstrap.run` and `Settings`. A change there needs a `feat` or `fix` commit whose message says
what moved, and a note in `docs/decisions.md` when it reverses a recorded decision.

## Releases

See [docs/runbooks/release.md](docs/runbooks/release.md).
