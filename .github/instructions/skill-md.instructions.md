---
applyTo: "skills/**/*.md"
---

# SKILL.md and profile-file instructions for Copilot

Files matched by this glob are runtime instructions consumed by an LLM agent (Claude Code) at audit time. They are NOT human-facing documentation.

## Critique these against runtime-correctness criteria

- **Ambiguity that an LLM would misclassify.** Words like "consider," "maybe," "if appropriate" without an explicit decision rule will produce inconsistent classifications across runs. A bullet that says "downgrade to LOW when …" is good; "review for downgrade" is not.
- **Missing graceful-degradation paths.** Every toolchain-using bash block in `skills/stub-audit/profiles/*.md` must end with `|| true` so the sweep does not abort the audit on a missing binary. Profiles also need a "Graceful degradation" table mapping each missing tool to the lost coverage and the fallback. Flag a profile that adds a new tool without the table entry.
- **Inconsistency with the structured-finding schema.** The schema lives in `skills/stub-audit/SKILL.md` ("Structured finding schema") and `skills/dishonest-code-audit/SKILL.md` (combined-report shape). Allowed field names are a closed set; the aggregator raises on unknown keys. Flag any new field name or severity label introduced in a SKILL.md or profile that the aggregator does not parse.
- **Inconsistency with the orchestrator's Task prompts.** Step 4 of `skills/dishonest-code-audit/SKILL.md` passes `known_clean_surfaces` into both specialists and tells them to emit matches as `FALSE-POSITIVE / INTENTIONAL` with the caller note. A profile or SKILL change that silently drops known-clean matches would break this contract.
- **Stale references.** The orchestrator references `silent-failure-hunter` from `pr-review-toolkit`. References to other plugin/agent names should match what is actually installable.

## Do not critique these as "unclear documentation"

- Prose written in the second person ("Open the surrounding 20-40 lines and answer four questions in order…"). This is correct for a runtime instruction; the audience is an agent following the steps, not a developer reading docs.
- Repeated invocation hints across SKILL.md and README.md. The repetition is intentional — the skill description is matched against user prompts independently from the README.
- Long Phase-3 judgment lists. The skill is judgment-first; the candidate-generation greps are leads, not findings. Critique the judgment criteria for ambiguity (see above), not for length.

## Style

- Lowercase by default in human-facing prose. No em dashes as casual separators.
- No emojis.
