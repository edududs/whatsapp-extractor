# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and releases follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-09-17

### Added

- Frozen WhatsApp message, address, media and watchlist models.
- Structural source, writer, store and publisher ports with callable filters and handlers.
- Ordered asyncio event bus with isolated handler failures and save-before-publish extraction.
- Neonize message source with bounded buffering, contact names and key-exchange filtering.
- Memory, append-only JSON Lines and SQL message stores.
- Per-account message isolation through PostgreSQL schemas or attached SQLite files.
- Alembic migrations with a revision history per account.
- Rich panel/JSON views and a logging fallback.
- TOML configuration with global and per-account watchlists, environment overrides and comment-preserving CLI edits.
- Commands for extraction, listing and pairing accounts, migrations, default account selection and watchlist management.
- Account-aware composition with injectable sources, filters, writers and handlers.
- Hypothesis strategies, message factory and reusable message-store contract.
- Domain, adapter, extraction and architecture tests with strict linting and type checks.
- Ubuntu and Windows continuous integration.

[Unreleased]: https://github.com/edududs/whatsapp-extractor/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/edududs/whatsapp-extractor/tree/v0.1.0
