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
- Shared SQLite or PostgreSQL database for pairing data and extracted messages.
- Rich panel/JSON views and a logging fallback.
- Environment-based settings, a command-line entry point and injectable composition.
- Hypothesis strategies, message factory and reusable message-store contract.
- Domain, adapter, extraction and architecture tests with strict linting and type checks.
- Ubuntu and Windows continuous integration.

[Unreleased]: https://github.com/edududs/whatsapp-extractor/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/edududs/whatsapp-extractor/tree/v0.1.0
