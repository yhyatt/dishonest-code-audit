# Repository instructions for Copilot

This repo ships a Claude Code plugin that audits codebases for "lying" code — silent failures and stub/placeholder code in user-visible paths. The plugin runs two specialist subagents in parallel and a deterministic Python aggregator merges their findings.

When reviewing PRs in this repo, weight the items below.

## Audience

Most Markdown files under `skills/**/SKILL.md` and `skills/**/profiles/*.md` are runtime instructions consumed by an LLM agent, not human documentation. Do not critique their prose for clarity-to-developers. Critique them for: ambiguity that would cause an LLM to misclassify a finding, missing fallback paths when a toolchain is absent, and consistency with the structured-finding schema documented in `skills/stub-audit/SKILL.md`.

## Load-bearing patterns — do not flag these

- **Prompt-injection guard** (~150 words prepended to Task prompts in `skills/dishonest-code-audit/SKILL.md`). The cost is upfront and the value is contingent; this is acknowledged in the README. Do not suggest removing or shortening it.
- **`$(cmd 2>&1 >/dev/null)` in test harnesses.** Captures stderr while discarding stdout. The redirection order is correct — it is processed left-to-right against the file-descriptor table. Verified by the passing `case-06-malformed` and `case-12-malformed-known-clean` fixtures, which assert non-empty stderr capture.
- **`set -euo pipefail` plus explicit per-command rescue** in `tests/run-aggregator-tests.sh` and `tests/run-fixtures.sh`. The harnesses set the strict-mode flags AND use `set +e`/`set -e` brackets around expected-to-fail commands. Do not suggest "add error handling"; check the surrounding bracket first.
- **"Fail loud, never silent" posture in `skills/dishonest-code-audit/lib/aggregate.py`.** The script raises `ValueError` with `file:line` on every malformed block, missing field, unknown severity, and malformed known-clean entry. Do not suggest "consider continuing on parse errors" — that defeats the script's stated motivation (the orchestrator LLM miscounts, and a silently-broken parser produces the same failure shape).
- **`npx --yes` for `knip` and `leasot` in `skills/stub-audit/profiles/typescript.md`.** The design goal is zero-install. Do not suggest pinning versions in the profile bash.
- **Unified `FALSE-POSITIVE / INTENTIONAL` severity label.** Canonical per the SKILL.md prompt. `normalize_severity()` accepts it and canonicalizes to `INTENTIONAL` for bucketing. Do not flag the long-form label as "non-canonical."
- **Hebrew strings in `tests/fixtures/**` and in example fixtures.** Some fixtures use Hebrew strings because the wet run was on a Hebrew app. Not a localization concern — these are test inputs, not user-facing copy.

## Real concerns to weight heavily

- **Counts arithmetic in `skills/dishonest-code-audit/lib/aggregate.py`.** Any change to `build_counts`, `apply_known_clean`, or `render_markdown` must keep the rendered equation reconciling against itself (`safe + mock - overlap - reclassified = total`). The reconciliation is asserted by `case-07-reclass-overlap`.
- **Dedup correctness in `deduplicate()`.** Two findings about the same real bug must merge; two unrelated findings in the same file must NOT merge. The Jaccard fallback is gated on "at least one side has unknown line" — flag any change that removes the gate.
- **Block parser tolerance.** The parser handles pipe-block evidence, multi-line continuations, blank-line spacing, and `Line: 40, 47, 57` lists. Any change that narrows tolerance must be backed by a new fixture; widening tolerance should not silently accept unknown top-level field keys (this used to silently truncate `User-visible lie` — see `case-08-strict-unknown-key`).
- **Profile additions.** A new language profile under `skills/stub-audit/profiles/<lang>.md` should mirror the existing profile structure (Detection bash, Always-skip patterns, Graceful degradation table) AND ship at least one fixture under `tests/fixtures/<lang>-<framework>/` that the run-fixtures harness exercises.

## House style

- Lowercase by default in human-facing prose. Avoid em dashes (`—`) used as casual sentence separators; use a comma, period, or colon. (See `README.md` and `CHANGELOG.md` for the established voice.)
- Test fixtures are minimal by policy — usually 1-2 findings per side. Do not suggest "make the fixture more realistic" unless it would exercise a real edge case the harness misses.
- No emojis in code or commit messages.
