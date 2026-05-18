---
name: New stack or framework profile
about: Add support for a stack (language) or framework not yet covered.
title: "[profile] "
labels: enhancement, profile
---

## Profile

- Stack or framework name:
- Detection signal (manifest file, dependency entry, file extension):
- Required toolchain, and toolchain-missing fallback:

## Patterns this profile should catch

List the dishonest-code patterns specific to this stack. Each one is a candidate generator plus a one-line description of what the user is lied to about.

- [ ] Pattern 1: <pattern> -> user sees <X>
- [ ] Pattern 2:
- [ ] Pattern 3:

## Contribution checklist

Mirror what the shipped profiles already do:

- [ ] `skills/stub-audit/profiles/<name>.md` (or `frameworks/<name>.md`)
- [ ] `tests/fixtures/<name>-<short>/` with at least one planted finding per pattern
- [ ] `expected.json` listing every planted finding
- [ ] `pattern_to_search` case in `run_profile_grep` inside `tests/run-fixtures.sh`, mirroring the profile's published grep
- [ ] Row added to the Supported stacks (or framework) table in `README.md`
- [ ] CHANGELOG entry under `## [Unreleased]`

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for the full guide.
