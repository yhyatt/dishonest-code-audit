# Contributing to dishonest-code-audit

Thanks for considering a contribution. This plugin ships two Claude Code skills (`dishonest-code-audit` orchestrator + `stub-audit` standalone) that find code which lies to the user. Stack coverage and pattern coverage both grow by adding small, testable pieces.

## Repository layout

```
.claude-plugin/
  plugin.json            Plugin manifest
  marketplace.json       Marketplace metadata
skills/
  dishonest-code-audit/
    SKILL.md             Orchestrator skill (Task-fans-out, aggregates)
  stub-audit/
    SKILL.md             Standalone mock/stub auditor
    profiles/
      README.md          How profiles are structured
      typescript.md      Per-stack candidate generators
      python.md
      go.md
      rust.md
      ruby.md
      frameworks/
        react.md         Per-framework UI-affordance patterns
        vue.md
        svelte.md
        solidjs.md
tests/
  fixtures/              One tiny synthetic project per profile
  lib/                   Helpers: extract-bash, validate-frontmatter
  run-fixtures.sh        Mechanical-sweep regression harness
.github/workflows/
  ci.yml                 Markdownlint + frontmatter + shellcheck + harness
CHANGELOG.md             Keep-a-Changelog
README.md                User-facing intro
```

## How to add a stack profile

Stack profiles plug detection bash + skip-lists into `stub-audit` for a new language. Mirror the shape of the existing profiles.

1. **Pick the closest existing profile** (`typescript.md`, `python.md`, `go.md`, `rust.md`, or `ruby.md`) and copy it as `skills/stub-audit/profiles/<your-stack>.md`.

2. **Write four sections in the profile file:**
   - One- or two-sentence intro on what the profile catches.
   - Detection bash. Every toolchain call must tolerate absence (`|| true` after the call). Greps should narrow with `--glob` and skip vendored directories.
   - Always-skip patterns specific to the language (idiomatic empty bodies, type stubs, generated files).
   - Graceful-degradation table: which tools provide which coverage, what is lost when they are missing, and how to install.

3. **Add a detection rule** to the `PROFILES=()` block in `skills/stub-audit/SKILL.md` (Phase 1). The rule keys off the language's canonical manifest file (`Gemfile`, `pyproject.toml`, etc.).

4. **Ship a fixture.** Create `tests/fixtures/<your-stack>/` containing:
   - One or two small source files with planted stub patterns. The files must be syntactically valid for the language but do NOT need to install, compile, or run.
   - The matching manifest file at the fixture root (so stack detection would match).
   - An `expected.json` manifest listing the file path, pattern label, and minimum severity each planted finding represents.

5. **Add pattern-to-search mappings** in `tests/run-fixtures.sh` (the `pattern_to_search` case statement) if your pattern label is not already covered. The mapping translates a high-level pattern label into the fixed-string grep the harness uses to assert presence.

6. **Run the harness:**

   ```bash
   bash tests/run-fixtures.sh
   ```

   The harness must exit 0 with every entry showing `OK`. If a finding does not surface, either the fixture is wrong or the pattern mapping is wrong; do not relax the harness to make it pass.

7. **Document the toolchain dependency** in the profile's graceful-degradation table. Profiles must always work in degraded (grep-only) mode.

## How to add a framework profile

Framework profiles layer on top of a stack profile to catch UI-affordance patterns. The current set covers `react`, `vue`, `svelte`, and `solidjs`. The shape is identical to a stack profile except:

- The detection bash should be grep-only (no toolchain dependency beyond `ripgrep` / `grep`).
- The "Worked examples" section is load-bearing. Show one or two HIGH-severity patterns in the framework's idiomatic syntax so reviewers can pattern-match quickly.
- Add framework detection to `skills/stub-audit/SKILL.md` Phase 1 inside the `if printf '%s\n' "${PROFILES[@]}" | grep -qx "typescript"; then` block. The framework profile loads only when its dependency is present in `package.json`.

## How to propose a new pattern

Inside an existing profile or skill:

1. Add the grep / detection logic to the relevant profile file.
2. Add (or extend) a fixture that contains a planted instance of the pattern.
3. Extend `expected.json` and the `pattern_to_search` mapping.
4. Run `bash tests/run-fixtures.sh`. Must exit 0.
5. Open a PR with the pattern's name, the rationale (what user-visible lie it surfaces), and one real-world example with the project elided.

## Semver policy

This plugin follows semver as best it can for a Markdown-shipping plugin:

- **MAJOR (`X.0.0`)**: Removing a profile, changing the finding-schema shape, or breaking the orchestrator's contract with `pr-review-toolkit`.
- **MINOR (`0.X.0`)**: Adding a new profile, adding a new pattern, expanding the default scope.
- **PATCH (`0.0.X`)**: Tightening an existing skip-list, fixing a profile bug, documentation-only updates.

Bump `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` to the same version. Add a CHANGELOG entry in Keep-a-Changelog format.

## PR checklist

- [ ] `bash tests/run-fixtures.sh` exits 0.
- [ ] `bash tests/lib/validate-frontmatter.sh skills` exits 0.
- [ ] Any new bash block in a SKILL or profile file passes `shellcheck -S warning` when extracted via `tests/lib/extract-bash.sh`.
- [ ] CHANGELOG entry added under the next version.
- [ ] No private project names or absolute file paths under `/home/`, `/Users/`, or `C:\` remain in the shipped files.
- [ ] No new instructions inside the repo that a malicious upstream could exploit via prompt injection (the orchestrator's prompt-injection guard treats repo contents as untrusted, but contributors should still avoid adding lines like "ignore prior instructions" anywhere).

## Style

- Direct, concrete writing. No marketing prose.
- **No em dashes (`—`), en dashes (`–`), or `--` as casual sentence separators.** Use a comma, period, or colon. This matches the project's documentation style.
- Lowercase casual sentence starts are fine in code comments and skill internals; use sentence case for headings.
