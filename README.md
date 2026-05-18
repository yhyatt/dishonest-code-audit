# dishonest-code-audit

[![CI](https://github.com/yhyatt/dishonest-code-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/yhyatt/dishonest-code-audit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Find code that lies to the user. The orchestrator runs two specialists in parallel against a scope (whole codebase / branch diff / specific directory) and aggregates their findings into one combined report.

- **`dishonest-code-audit`** (orchestrator, ships here): spawns the two specialists below in parallel and aggregates their findings.
- **`silent-failure-hunter`** (error-path specialist): reasons about catch blocks, fallback logic, and log-and-continue patterns. Ships in [`pr-review-toolkit`](https://github.com/anthropics/claude-plugins-official) and must be installed separately, see [Prerequisites](#prerequisites).
- **`stub-audit`** (happy-path specialist, ships here): mock/stub/placeholder auditor. Wraps language-specific tools (knip + leasot for JS/TS, vulture for Python, `go vet` for Go, `cargo clippy` for Rust, rubocop for Ruby) plus a tuned grep sweep to build a candidate list, then uses LLM judgment to classify each finding by UX impact (HIGH / MEDIUM / LOW / FALSE-POSITIVE / INTENTIONAL). Can be invoked standalone.

## Why this exists

Born from a real pre-ship audit of a Next.js + Supabase + TypeScript codebase. The audits caught:

- Two HIGH live-tournament correctness bugs (player submits answer, server returns 5xx, UI advances as if successful).
- Three MEDIUM clipboard liar-toasts (toast string fires even when `writeText` rejected).
- One HIGH host-side "abandon session" handler that navigated away without telling the server.
- One HIGH hand-drawn SVG "QR code" that did not encode its `value` prop.
- One HIGH labelled action button with empty `onClick` and a stale `// TODO(slice-12)` marker.

All of those landed on `main` despite passing manual review. The skill exists because static analysis cannot tell you whether a stub matters; the model can, given the right candidate list and the right judgment lens.

## Supported stacks

| Stack          | Profile file                                  | Toolchain used                  | Toolchain-missing fallback                            |
| -------------- | --------------------------------------------- | ------------------------------- | ----------------------------------------------------- |
| TypeScript/JS  | `skills/stub-audit/profiles/typescript.md`    | `npx knip`, `npx leasot`        | Grep-only (TODO scan + stub-named variables)          |
| Python         | `skills/stub-audit/profiles/python.md`        | `vulture`, `npx leasot`         | Grep-only (`raise NotImplementedError`, bare `pass`)  |
| Go             | `skills/stub-audit/profiles/go.md`            | `go vet`                        | Grep-only (`panic("not implemented")`, empty methods) |
| Rust           | `skills/stub-audit/profiles/rust.md`          | `cargo clippy`                  | Grep-only (`todo!()`, `unimplemented!()`)             |
| Ruby           | `skills/stub-audit/profiles/ruby.md`          | `rubocop`                       | Grep-only (`raise NotImplementedError`, empty `def`)  |

UI framework patterns layer on top of the TypeScript profile when the matching dependency is present in `package.json`:

| Framework | Profile file                                            | Detected via                |
| --------- | ------------------------------------------------------- | --------------------------- |
| React     | `skills/stub-audit/profiles/frameworks/react.md`        | `"react"` in package.json   |
| Vue       | `skills/stub-audit/profiles/frameworks/vue.md`          | `"vue"` in package.json     |
| Svelte    | `skills/stub-audit/profiles/frameworks/svelte.md`       | `"svelte"` in package.json  |
| SolidJS   | `skills/stub-audit/profiles/frameworks/solidjs.md`      | `"solid-js"` in package.json |

Adding a new stack profile is a small, testable change. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Prerequisites

The orchestrator (`dishonest-code-audit`) calls `silent-failure-hunter`, which ships in Anthropic's `pr-review-toolkit` plugin. Install it first:

```bash
claude plugin install pr-review-toolkit@claude-plugins-official
```

`stub-audit` works standalone without `pr-review-toolkit`.

Optional toolchains lift coverage for each stack. See the table above. None are required; profiles degrade to grep-only and report the gap in the audit's Coverage notes section.

## Install

Once published to GitHub:

```bash
claude plugin install yhyatt/dishonest-code-audit
```

For local development (or before publishing):

```bash
claude plugin install /absolute/path/to/dishonest-code-audit
```

Or load just for the current session without installing:

```bash
claude --plugin-dir /absolute/path/to/dishonest-code-audit
```

Restart Claude Code after `claude plugin install` so the skills become available.

## Use

Trigger by name or by describing the job in any session:

- *"Run a dishonest code audit on this branch"*
- *"Pre-ship audit before I merge"*
- *"What's fake in this codebase?"*
- *"Production-readiness sweep"*

For the standalone mock/stub auditor only:

- *"Run a stub audit"* / *"Find stale TODOs"* / *"What's still a placeholder?"*

## Output

Each audit writes a markdown report:

- `<output-dir>/SAFE-FAIL-AUDIT.md` (from silent-failure-hunter)
- `<output-dir>/MOCK-STUB-AUDIT.md` (from stub-audit)
- `<output-dir>/DISHONEST-CODE-AUDIT.md` (combined, deduplicated, written by the orchestrator)

Default `<output-dir>` is `.dishonest-code-audit-<YYYY-MM-DD>/` at the repo root. Project-specific conventions (e.g., `.slice-XX-prep/`) are honored only when the caller passes an explicit directory.

Every HIGH and MEDIUM finding is emitted as a structured block the orchestrator can parse and deduplicate deterministically. See the schema in `skills/stub-audit/SKILL.md` ("Structured finding schema").

## Classification

Both specialists use a shared severity model:

- **HIGH**: user sees a broken affordance, or believes the action succeeded when it didn't. Block before ship.
- **MEDIUM**: real concern documented in code (TODO, stale workaround) but doesn't currently lie to the user.
- **LOW**: cosmetic markers, defensive defaults, intentional safe-fails with explanatory comments.
- **FALSE-POSITIVE / INTENTIONAL**: pattern matches but is correct behavior.

If the two specialists disagree on severity for the same site, the combined report uses the higher severity and records both opinions.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a stack profile, propose a new pattern, and pass the fixture harness.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT.
