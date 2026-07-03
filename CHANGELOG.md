# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `Provider`/resource options: `ca_cert` (verify against a private CA),
  `job_timeout_s`, `poll_interval_s`.
- jsonrpc transport: connection retry with backoff on transient failures;
  connect timeout.
- API key redaction in raised error messages.
- `docs/operations.md`: concurrency (`--parallel 1`), timeout, and TLS tuning.

## [0.1.0] - 2026-07-03

Initial release.

### Added
- `Provider` component holding TrueNAS connection settings (host, transport,
  credentials, TLS).
- Two transports: `jsonrpc` (JSON-RPC over WebSocket, recommended) and
  `midclt_ssh` (ssh + midclt).
- Resources:
  - `CatalogApp` — official catalog apps (create/read/update/delete, upgrade on
    version change, structured `values` diff).
  - `CustomApp` — custom apps from Docker Compose YAML.
  - `Dataset` — ZFS datasets via `pool.dataset.*` (safe delete by default).
  - `Directory` — host directories via SSH (safe no-op delete).
- Input validation (`check`) for all resources: app-name regex, transport,
  required fields, dataset pool-paths, absolute directory paths.
- `pulumi import` support (import-safe `read`) + adopt-on-create.
- API key resolution chain: Pulumi secret config → `$TRUENAS_API_KEY` → `.env`;
  keys are Pulumi secrets (encrypted in state, masked in logs).
- Examples: `minimal`, `custom-app`, `arr-stack`.
- Docs: resources, authentication, importing.

### Notes
- Verified against TrueNAS 25.10.x.
- `values` for catalog apps are passed through unchanged (per-app,
  per-version schemas); use `scripts/preflight.py` to discover them.

[Unreleased]: https://github.com/yehia2amer/pulumi-truenas/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yehia2amer/pulumi-truenas/releases/tag/v0.1.0
