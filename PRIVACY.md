# Privacy

This plugin collects no data, sends no telemetry, and makes no network calls of its own.

## What runs locally

- The two skills (`dishonest-code-audit`, `stub-audit`) are markdown files that instruct the Claude Code session. They execute entirely inside that session.
- The bash helpers (`tests/run-fixtures.sh`, `tests/lib/*.sh`) and the per-stack profile commands (`rg`, `grep`, `npx knip`, `npx leasot`, `vulture`, `go vet`, `cargo clippy`, `rubocop`) run on the user's machine, against the user's own source files.
- Reports are written to a local directory (default `.dishonest-code-audit-<YYYY-MM-DD>/` at the repo root). Nothing is uploaded anywhere by this plugin.

## What the underlying tools may do

- **Claude Code itself** sends conversation context, including any source-file excerpts the model reads, to Anthropic's API. That is governed by [Anthropic's privacy policy](https://www.anthropic.com/legal/privacy) and the user's Claude Code configuration. This plugin does not change what Claude Code does or does not send.
- **`npx knip` and `npx leasot`** may resolve and download packages from npm on first run. That traffic is between the user's machine and the npm registry; the plugin does not proxy or inspect it.
- **Language toolchains** (`vulture`, `go vet`, `cargo clippy`, `rubocop`) operate on local files and emit local output.

## Repository data

- Issues, pull requests, and discussions filed on `github.com/yhyatt/dishonest-code-audit` are public. Do not paste source code you cannot share publicly into a public issue. Sensitive reports belong in [SECURITY.md](SECURITY.md).

## Questions

hyatt.yonatan@gmail.com
