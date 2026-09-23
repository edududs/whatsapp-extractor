# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and releases follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). git-cliff generates it from the
commit history: do not edit it by hand.

Before 1.0 the public contract still moves: `MINOR` adds features and may change the contract,
`PATCH` fixes.

## [0.2.1] - 2026-09-18

### Added

- Log the effective watchlist when a run starts

## [0.2.0] - 2026-09-18

### Added

- **cli:** List the groups an account belongs to
- **config:** Allow messages to live apart from the session database

## [0.1.0] - 2026-09-18

### Added

- **domain:** Define WhatsApp messages and watchlist rules
- **application:** Define ports and ordered event dispatch
- **adapters:** Map and stream neonize messages
- **adapters:** Persist messages in memory, JSON Lines and SQL
- **adapters:** Add terminal views and logging fallback
- Compose configurable extraction and executable entry points
- **testing:** Provide strategies, factory and store contract
- **storage:** Separate account stores and migrate their schemas
- **config:** Load TOML settings and preserve comments in CLI edits
- **cli:** Manage paired accounts and extraction settings

### Documentation

- Document usage and the initial MIT release
- Explain account isolation and the configuration workflow

### Tests

- Verify domain rules, adapters and layer boundaries
- Verify account isolation, TOML precedence and CLI behavior

### Infrastructure

- Initialize Python tooling and package metadata
- Check formatting, types and tests on Linux and Windows
- Exclude local directories from source distributions

[0.2.1]: https://github.com/edududs/whatsapp-extractor/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/edududs/whatsapp-extractor/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/edududs/whatsapp-extractor/tree/v0.1.0

