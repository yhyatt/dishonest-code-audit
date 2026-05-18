---
applyTo: "tests/fixtures/**"
---

# Test-fixture instructions for Copilot

Files under `tests/fixtures/**` are **inputs to the test harness**, not production code. They are deliberately crafted to exercise specific detection patterns or parser edge cases.

## Do not flag

- **Planted "broken" code** (empty handlers, `panic("not implemented")`, `raise NotImplementedError`, hardcoded sample data in route handlers, `todo!()`). These are the targets the skill is designed to detect. Each fixture's `expected.json` records which findings the harness asserts.
- **Stub-shaped variable names** (`mockFoo`, `fakeFoo`, `dummyFoo`) in non-test paths under `tests/fixtures/<stack>-*/`. The harness verifies the profile sweep surfaces these.
- **Malformed input** inside `tests/fixtures/aggregator/case-06-malformed/` and `tests/fixtures/aggregator/case-12-malformed-known-clean/`. The harness asserts the aggregator exits non-zero on these inputs. Do not "fix" the malformed input.
- **Tiny or single-line files.** Fixtures are minimal by policy — usually 1-2 findings per side. A 5-line `safe-fail.md` is not "missing content."
- **Hebrew strings.** Some fixtures carry Hebrew strings to mirror the wet-run corpus. Not a localization concern.

## Do flag

- A fixture's planted finding NOT being asserted in its `expected.json` (orphan planted code → harness coverage gap).
- An `expected.json` whose counts do not arithmetically reconcile (e.g. `safe_high: 2, mock_high: 0, high_overlap: 0, high_total: 1`).
- A new fixture under `tests/fixtures/aggregator/` that does not exercise a distinct dedup, severity-merge, reclassification, or fail-loud branch versus the existing 12 cases.
- A fixture's `expected.json` that asserts behavior contradicting the aggregator's documented spec in `skills/dishonest-code-audit/SKILL.md`.
