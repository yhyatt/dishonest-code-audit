# Changelog

All notable changes to this plugin are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the plugin tries to follow [semantic versioning](https://semver.org/spec/v2.0.0.html) within the constraints of a Markdown-shipping plugin.

## [0.2.0]

### Added

- **Pluggable stack profiles.** `stub-audit` now loads per-stack candidate generators from `skills/stub-audit/profiles/`: `typescript.md`, `python.md`, `go.md`, `rust.md`, `ruby.md`. Each profile owns its detection bash, language-specific skip-list, and graceful-degradation behavior when its toolchain is missing.
- **Pluggable framework profiles** for UI-affordance patterns: `frameworks/react.md`, `frameworks/vue.md`, `frameworks/svelte.md`, `frameworks/solidjs.md`. Loaded on top of the typescript profile when the matching dependency is present in `package.json`.
- **Structured finding schema** shared across both specialists. Each HIGH/MEDIUM finding is emitted as a parseable block (`Finding ID`, `Severity`, `File`, `Line`, `User-visible lie`, `Evidence`, `Recommended fix`, `Fix size`, `Confidence`). The orchestrator's aggregator parses these blocks deterministically and deduplicates on `(normalized File, Line)` with a `User-visible lie` similarity fallback when either field is `unknown`.
- **Prompt-injection guard** prepended to both Task-tool prompts. Treats all repository contents as untrusted input. If a file says "ignore prior instructions" or "do not report this," it gets reported as a finding.
- **Explicit `## Requires` section** at the top of both SKILLs. Lists runtime assumptions (Task tool, `pr-review-toolkit`, language toolchains) and graceful-degradation behavior.
- **Quiet, scripted-friendly prerequisite check** for `pr-review-toolkit`. Replaces a noisy grep with a check that exits with a clear error message.
- **Broader default scope.** Default glob is now `{app,src,pages,components,lib,server,hooks,utils,actions,api,routes}/**/*.{ts,tsx,js,jsx,mjs,cjs,mts,cts,py,go,rs,rb}`, conditioned on detected stack profiles. Excludes `node_modules`, `.next`, `dist`, `build`, `coverage`, `target`, `.venv`, `venv`, `__pycache__`, `vendor`, lockfiles, and `@generated` headers.
- **Coverage notes section** in the combined report. Lists profiles loaded, file globs scanned and excluded, tools that ran vs. were unavailable.
- **Test fixtures + CI.** Tiny synthetic projects under `tests/fixtures/` for each stack profile, with an `expected.json` manifest. `tests/run-fixtures.sh` validates that every planted pattern surfaces in its fixture. `.github/workflows/ci.yml` runs markdownlint, frontmatter validation, shellcheck on bash blocks extracted from SKILLs, and the fixture harness.
- **OSS hygiene docs.** `CONTRIBUTING.md` (repo layout, how to add a profile, semver policy, PR checklist), `CHANGELOG.md` (this file).

### Changed

- Severity vocabulary unified across both specialists. `NONE-INTENTIONAL` (from safe-fail) and the bare `FALSE-POSITIVE` (from stub-audit) are replaced with a single `FALSE-POSITIVE / INTENTIONAL` label.
- Findings with `Line: unknown` are retained by the aggregator. File-level lies (e.g., a whole route handler returning canned data) are common HIGH severities and must not be dropped.
- When specialists disagree on severity for the same dedup key, the combined entry uses the higher severity and records both opinions.
- Default output directory is now `.dishonest-code-audit-<YYYY-MM-DD>/` at the repo root. Project-specific conventions (e.g., `.slice-XX-prep/`) are honored only when the caller explicitly passes a directory.
- Softened the "research showed" claim in the orchestrator's preamble. The reason to keep two specialists is that the review frames are intentionally different, not the result of a study.
- README restructured around supported stacks (table), prerequisites, install, use, output, and classification. Links out to `CONTRIBUTING.md` and `CHANGELOG.md`.

### Removed

- Project-specific tuning section that named a private codebase ("ballpark") and referenced an absolute path on the author's machine. Replaced with a neutral "Worked examples" section.
- Inline grep sweep in `stub-audit/SKILL.md` Phase 2, moved into the per-stack and per-framework profile files.

### Fixed

- Patterns inside single-quoted bash strings that mixed unescaped single quotes now use `\x27` so the extracted bash blocks pass `bash -n` and `shellcheck -S warning`.

## [0.1.0]

### Added

- Initial release of plugin + two skills (`dishonest-code-audit` orchestrator, `stub-audit` standalone).

[0.2.0]: https://github.com/yhyatt/dishonest-code-audit/releases/tag/v0.2.0
[0.1.0]: https://github.com/yhyatt/dishonest-code-audit/releases/tag/v0.1.0
