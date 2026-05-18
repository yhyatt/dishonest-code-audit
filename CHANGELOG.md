# Changelog

All notable changes to this plugin are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the plugin tries to follow [semantic versioning](https://semver.org/spec/v2.0.0.html) within the constraints of a Markdown-shipping plugin.

## [Unreleased]

### Known limitations

- Stack detection only inspects the repo root. Monorepos with manifests under `apps/*/`, `packages/*/`, `services/*/` will not auto-load their stacks' profiles. Workaround: invoke from the relevant subdirectory, or pass an explicit scope. Long-term: walk a bounded depth or consult workspace manifests.

## [0.3.0]

### Added

- **Deterministic Python aggregator** at `skills/dishonest-code-audit/lib/aggregate.py`. Parses both source reports block-by-block, dedups on `(normalize_path(File), line_primary)` with a Jaccard-≥0.6 fallback on `User-visible lie` when line is unknown, max-merges severity (records disagreement), applies known-clean reclassification, and emits two artifacts: `AGGREGATE.json` (single source of truth — findings, counts, dedup pairings, `single_source_findings` array for the cross-audit-gaps narrative) and `DISHONEST-CODE-AUDIT.md` (skeleton with mechanical sections filled and `<!-- LLM_FILL: ... -->` placeholders for headline, dominant patterns, cross-audit gaps). Fails loud on every malformed input.
- **`known_clean_surfaces`** as a first-class structured parameter in the orchestrator's step 1. Passed verbatim into both specialist prompts. Matched entries are classified `FALSE-POSITIVE / INTENTIONAL` with the caller's reason recorded. Unmatched entries surface in a "not observed in this run" subsection so a typoed path cannot falsely claim verification.
- **`--case-insensitive-paths`** CLI flag on the aggregator. Casefolds `File:` values during dedup. Off by default (Linux is case-sensitive); opt-in for macOS APFS / Windows NTFS.
- **`try/finally`-with-throw-no-catch candidate sweep** in `skills/stub-audit/profiles/typescript.md`. Phase-3 judgment verifies absence-of-catch in the enclosing function. Catches the silent-success mutation-handler pattern that surfaced in the second wet run (host clicks button, RPC fails, spinner clears, no toast). Framed as redundant double-coverage with `silent-failure-hunter`.
- **`Cross-audit gaps (tuning signal)` as a REQUIRED section** in the combined-report template. Records cases where one specialist caught a finding the other could in principle have caught from its own framing. Drives the pattern-coverage tuning loop.
- **Aggregator-side `MEDIUM → LOW` demotion rule** with required `Demoted from MEDIUM: <reason>` annotation. Silent demotion forbidden — verdict counts must reconcile against the source reports plus recorded demotions.
- **Aggregator regression harness** at `tests/run-aggregator-tests.sh` and 17 fixture cases under `tests/fixtures/aggregator/`. Covers exact overlap, fuzzy overlap, fuzzy miss, severity disagreement, known-clean reclassification (matched + unmatched + path-normalize), strict unknown-key handling, blank-line tolerance, unified-label normalization, fuzzy best-match, duplicate-within-source fail-loud, missing-known-clean-path fail-loud, case-insensitive paths. CI runs both `run-fixtures.sh` and `run-aggregator-tests.sh`.
- **Copilot custom instructions**. `.github/copilot-instructions.md` (repo-wide) plus path-scoped `.github/instructions/fixtures.instructions.md` and `.github/instructions/skill-md.instructions.md` calling out load-bearing patterns automated reviewers misread (bash redirection in test harnesses, fail-loud posture, unified `FALSE-POSITIVE / INTENTIONAL` label, `npx --yes` zero-install design, planted fixture content vs real production code).

### Changed

- Orchestrator step 5 now invokes the deterministic aggregator and then fills three narrative placeholders. Previous behavior relied on the orchestrator LLM for block-by-block parsing.
- **Severity merge under disagreement reconciles arithmetically.** Per-source counts are computed against effective merged severity, so `safe-fail HIGH + mock-stub MEDIUM → HIGH` contributes 1 to each of `safe_high` / `mock_high` and the MEDIUM is correctly absent from the MEDIUM equation. Restores the `safe + mock - overlap - reclassified = total` invariant for every bucket.
- **Block parser tolerance.** Blank lines inside structured blocks are tolerated as visual spacing; the block terminates only at the next `### Finding ID:` header or EOF.
- **Unknown top-level field keys are no longer silently captured.** A wrapped `User-visible lie` continuation that happens to begin with `Capital: word` is preserved as part of the previous field rather than truncating it.
- **Fuzzy match picks the highest-scoring candidate** over the threshold, not the first. Prevents misrouting when multiple unknown-line findings sit in the same file.
- **`apply_known_clean()`** runs caller-supplied paths through the same `normalize_path` logic used on `File:` values, so `./src/Foo.tsx` matches an aggregator-normalized `src/Foo.tsx`. Honors `--case-insensitive-paths`.
- **Unified `FALSE-POSITIVE / INTENTIONAL` label** is normalized to `INTENTIONAL` at parse time. Downstream lookups never miss.
- README: "Why this exists" expanded to cover both wet runs. Second-wet-run section names the two dominant patterns (7-handler `try/finally`-no-catch in HostControlRoom, state-endpoint missing-`error`-field leaking as 200 OK with empty payloads). New "Deterministic aggregator" subsection. New example 1a demonstrates `known_clean_surfaces` matched-vs-not-observed.
- README: "Two specialists, near-disjoint surfaces" framing made explicit. The specialists are complementary, not redundant; dedup overlap is the exception.

### Fixed

- Aggregator counts arithmetic reconciles under known-clean reclassification. A `reclassified by known_clean_surfaces` term appears in the rendered equation when applicable.
- Duplicate `(file, line_primary)` within a source no longer silently overwrites the dedup index. Raises with both colliding finding IDs and the source `path:line`.
- `--known-clean-surfaces` with a non-existent path now exits 2 with the missing path named in stderr (was silent no-op).
- Malformed `known_clean_surfaces` entries (non-blank, non-comment line not matching `path[:symbol] — reason`) raise with `file:line` and the offending text (was silent skip).
- Orchestrator step-5 bash invocation snippet uses a workable script-location pattern instead of the non-functional `$(realpath "$0")`.

## [0.2.2]

### Added

- `PRIVACY.md`: explicit "no data collected, no telemetry, no network calls" statement. Names what the underlying tools (Claude Code itself, `npx`, language toolchains) may do, and points sensitive reports at `SECURITY.md`. Added for the `claude-plugins-official` marketplace submission form's Privacy policy URL field.

## [0.2.1]

### Added

- README badges (CI status, MIT license) under the H1.
- README `## Examples` section: five concrete use cases (pre-ship sweep, inherited-code stub audit, FastAPI pre-merge gate, stale-TODO sweep, scoped audit). Doubles as the source for the marketplace submission's "how users use the plugin" question.
- OSS hygiene: `SECURITY.md` (vulnerability reporting + threat model), `CODE_OF_CONDUCT.md` (adopts Contributor Covenant 2.1 by reference), `.github/ISSUE_TEMPLATE/bug.md`, `.github/ISSUE_TEMPLATE/new-profile.md`, `.github/PULL_REQUEST_TEMPLATE.md`.

### Changed

- README skill list: `silent-failure-hunter` is now named explicitly alongside the two skills that ship here, with the `pr-review-toolkit` dependency made obvious at first read. Previously the "Spawns both audits below" sentence described two skills but the list only named one.

### Fixed

- Marketplace `metadata.version` and plugin `version` bumped to `0.2.1`.

## [0.2.0]

### Added

- **Pluggable stack profiles.** `stub-audit` now loads per-stack candidate generators from `skills/stub-audit/profiles/`: `typescript.md`, `python.md`, `go.md`, `rust.md`, `ruby.md`. Each profile owns its detection bash, language-specific skip-list, and graceful-degradation behavior when its toolchain is missing.
- **Pluggable framework profiles** for UI-affordance patterns: `frameworks/react.md`, `frameworks/vue.md`, `frameworks/svelte.md`, `frameworks/solidjs.md`. Loaded on top of the typescript profile when the matching dependency is present in `package.json`.
- **Structured finding schema** shared across both specialists. Each HIGH/MEDIUM finding is emitted as a parseable block (`Finding ID`, `Severity`, `File`, `Line`, `User-visible lie`, `Evidence`, `Recommended fix`, `Fix size`, `Confidence`). The orchestrator's aggregator parses these blocks block-by-block, tolerates minor formatting variance, and deduplicates on `(normalized File, Line)` with a `User-visible lie` similarity fallback when either field is `unknown`.
- **Prompt-injection guard** prepended to both Task-tool prompts. Treats all repository contents as untrusted input. Any text that tries to redirect the audit's scope, severity, or skip-list is itself a finding, regardless of phrasing (worked examples documented in both SKILLs).
- **Explicit `## Requires` section** at the top of both SKILLs. Lists runtime assumptions (Task tool, `pr-review-toolkit`, language toolchains) and graceful-degradation behavior.
- **Quiet, scripted-friendly prerequisite check** for `pr-review-toolkit`. Replaces a noisy grep with a check that exits with a clear error message.
- **Broader default scope.** Default glob is now `{app,src,pages,components,lib,server,hooks,utils,actions,api,routes}/**/*.{ts,tsx,js,jsx,mjs,cjs,mts,cts,vue,svelte,py,go,rs,rb}`, conditioned on detected stack profiles. Excludes `node_modules`, `.next`, `dist`, `build`, `coverage`, `target`, `.venv`, `venv`, `__pycache__`, `vendor`, lockfiles, and `@generated` headers.
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

[0.3.0]: https://github.com/yhyatt/dishonest-code-audit/releases/tag/v0.3.0
[0.2.2]: https://github.com/yhyatt/dishonest-code-audit/releases/tag/v0.2.2
[0.2.1]: https://github.com/yhyatt/dishonest-code-audit/releases/tag/v0.2.1
[0.2.0]: https://github.com/yhyatt/dishonest-code-audit/releases/tag/v0.2.0
[0.1.0]: https://github.com/yhyatt/dishonest-code-audit/releases/tag/v0.1.0
