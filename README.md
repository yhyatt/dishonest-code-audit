# dishonest-code-audit

[![CI](https://github.com/yhyatt/dishonest-code-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/yhyatt/dishonest-code-audit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Find code that lies to the user. The orchestrator runs two specialists in parallel against a scope (whole codebase / branch diff / specific directory) and aggregates their findings into one combined report.

- **`dishonest-code-audit`** (orchestrator, ships here): spawns the two specialists below in parallel and aggregates their findings.
- **`silent-failure-hunter`** (error-path specialist): reasons about catch blocks, fallback logic, and log-and-continue patterns. Ships in [`pr-review-toolkit`](https://github.com/anthropics/claude-plugins-official) and must be installed separately, see [Prerequisites](#prerequisites).
- **`stub-audit`** (happy-path specialist, ships here): mock/stub/placeholder auditor. Wraps language-specific tools (knip + leasot for JS/TS, vulture for Python, `go vet` for Go, `cargo clippy` for Rust, rubocop for Ruby) plus a tuned grep sweep to build a candidate list, then uses LLM judgment to classify each finding by UX impact (HIGH / MEDIUM / LOW / FALSE-POSITIVE / INTENTIONAL). Can be invoked standalone.

### Two specialists, near-disjoint surfaces

The two specialists are **complementary**, not redundant. They reason from different directions and find near-disjoint sets of issues on a real codebase. `silent-failure-hunter` audits failed operations (catch blocks, fallbacks, log-and-continue). `stub-audit` audits fake successful affordances (empty handlers, placeholder data, stale TODOs). Most findings sit on one specialist's domain, not both. Expect dedup overlap to be the exception, not the rule.

The combined report includes a `Cross-audit gaps (tuning signal)` section that records cases where one specialist caught a finding the other could have caught independently. These flag opportunities to strengthen the weaker specialist's pattern coverage over time, not bugs in the current run.

### What the prompt-injection guard costs you

Each specialist's prompt is prepended with a ~150-word guard treating repository contents as untrusted input. That cost is paid upfront on every audit. Its value is contingent — it only matters on repositories where a hostile or compromised file tries to redirect the audit. Keep it; the cost is small and the failure mode without it is silent.

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

## Examples

### 1. Pre-ship sweep on a feature branch (Next.js + TypeScript)

Before merging or deploying:

> "Run a dishonest code audit on this branch before I deploy."

The orchestrator auto-detects the TypeScript and React profiles, scopes the diff to `app/`, `components/`, `lib/`, and writes a combined `DISHONEST-CODE-AUDIT.md` with HIGH/MEDIUM/LOW findings. Typical HIGH catches on a real feature branch: a labeled button with empty `onClick`, a route handler returning canned mock data, a toast that fires inside a `.catch` after the server already returned 5xx.

### 2. Stub audit on inherited or older code

Drop into a repo you did not write:

> "What is still a stub or placeholder in this codebase?"

Triggers `stub-audit` standalone (no `pr-review-toolkit` required). Returns a curated list of empty handlers, mock-data route returns, placeholder SVGs that ignore their input prop, and stale TODOs cross-referenced against the project's backlog or plan files.

### 3. Pre-merge gate on a Python FastAPI service

> "Production-readiness check on this branch."

The Python profile catches `raise NotImplementedError` in route handlers, bare `def x(): pass` with no real implementation, and FastAPI endpoints returning placeholder dicts. The orchestrator runs `silent-failure-hunter` in parallel to catch swallowed exceptions in the same diff.

### 4. Stale-TODO sweep at the end of a sprint

> "Find stale TODOs that were supposed to land this sprint."

`stub-audit` cross-references every `TODO`/`FIXME`/`HACK` marker against the project's plan and backlog files. Tracked TODOs are LOW; untracked TODOs on a shipped milestone are MEDIUM at minimum, even when the code path is currently dormant.

### 5. Scoped audit on a specific directory or service

In a large codebase or monorepo:

> "Run the dishonest code audit on `src/billing/` only."

Orchestrator narrows the scope to that path. Useful for keeping the combined report under one screen on big codebases, or for auditing one service in a multi-service repo.

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
