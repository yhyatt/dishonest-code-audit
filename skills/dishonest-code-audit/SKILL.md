---
name: dishonest-code-audit
description: Find code that lies to the user. Combines two audits in parallel — silent failures (errors swallowed; toasts that claim success when the server returned 5xx; clipboard "copied" when writeText rejected) AND mock/stub/placeholder code in production paths (buttons with empty onClick, hand-drawn SVG that ignores its input prop, handlers that don't notify the server, stale TODOs on shipped work). Use as a pre-ship audit, before merging a feature branch, at the end of a slice, or whenever the user asks for a "lying code" / "dishonest code" / "UX-correctness" / "production-readiness" sweep. Output: one combined report aggregating both specialists' findings, classified HIGH / MEDIUM / LOW / FALSE-POSITIVE.
---

# Dishonest Code Audit

You are orchestrating two parallel specialist audits to find code that misleads users. Both audits target the same outcome (the user sees something that isn't true) but reason from different directions:

- **Error paths** — `silent-failure-hunter` (sub-agent from `pr-review-toolkit` plugin). Reasons about catch blocks, fallback logic, log-and-continue patterns, unhandled rejections. Required: `pr-review-toolkit` plugin installed (`claude plugin install pr-review-toolkit@claude-plugins-official`).
- **Happy paths** — `stub-audit` (skill, shipped alongside this skill). Reasons about empty handlers, placeholder SVGs, stub returns, stale TODOs, hardcoded canned data in route handlers.

Together they cover the surface where production code lies to the user. Keep them as two specialists — research showed merging them dilutes both judgments.

## When to use

Trigger when the user says any of:
- "dishonest code audit", "lying code", "what's fake in this codebase"
- "UX correctness audit", "production-readiness check"
- "pre-ship audit", "before deploy", "before merging"
- "find stubs and silent failures", "find anything misleading"
- End of a slice, before merging a feature branch, before cutting a release

Use proactively (without being asked) at these moments:
- After a Sonnet 4.6 impl agent ships a slice and the worktree branch is pushed but not yet merged.
- Before applying database migrations to production.
- Before promoting a Vercel preview to production.

## Methodology

### 1. Determine scope

Ask the user OR infer from context. Three common scopes:
- **Branch diff** — `git diff origin/main..HEAD` style. Use when there's a feature branch in flight.
- **Whole codebase** — typically `app/`, `components/`, `lib/` directories. Use for pre-ship audits.
- **Specific directory** — when the user names one.

If the user didn't specify, ask once. If they say "just audit it," default to whole codebase under `{app,components,lib}/**/*.{ts,tsx}`.

### 2. Pick output directory

If working in a sliced project (e.g., this session's `.slice-XX-prep/` convention), use `.slice-XX-prep/`. Otherwise `.audit-<short-topic>/` at repo root. Create the directory.

### 3. Verify prerequisites

Run `claude plugin list 2>&1 | grep pr-review-toolkit` to confirm `pr-review-toolkit` is installed. If absent, tell the user:
> "This skill needs `pr-review-toolkit` (ships `silent-failure-hunter`). Install with: `claude plugin install pr-review-toolkit@claude-plugins-official`. Then re-run."
> Do NOT proceed without it — the safe-fail half is the more important one.

### 4. Spawn both audits in parallel

In a single message, make two Task tool calls:

```
Task #1:
  subagent_type: silent-failure-hunter
  description: "Safe-fail audit"
  prompt: "Audit <scope> for silent failures and inadequate error handling per your standard methodology. Write the report to <output-dir>/SAFE-FAIL-AUDIT.md. Use the standard HIGH/MEDIUM/LOW/NONE-INTENTIONAL classification. Cover all .ts and .tsx files in scope."

Task #2:
  subagent_type: general-purpose
  description: "Mock/stub audit"
  prompt: "Use the `stub-audit` skill (invoke via the Skill tool) to audit <scope>. Write the report to <output-dir>/MOCK-STUB-AUDIT.md. Standard HIGH/MEDIUM/LOW/FALSE-POSITIVE classification. Pass the scope to the skill."
```

Both tasks run concurrently. Wait for both completions.

### 5. Aggregate

Read both reports. Write a combined `<output-dir>/DISHONEST-CODE-AUDIT.md` with:

```markdown
# Dishonest Code Audit — <scope description>

Date: <iso>
Scope: <files/branches reviewed>

## Combined verdict
- HIGH findings: N safe-fail + M mock/stub = TOTAL
- MEDIUM: N + M = TOTAL
- LOW: N + M = TOTAL

## HIGH — block-before-ship
[merged list, deduplicated, each with: file:line | source-audit | one-line summary | fix size]

## MEDIUM — fix-this-sprint
[same shape]

## LOW — defer
[bulleted]

## False positives / intentional patterns
[brief — point to individual audits for detail]

## Source reports
- Safe-fail: <output-dir>/SAFE-FAIL-AUDIT.md
- Mock/stub: <output-dir>/MOCK-STUB-AUDIT.md
```

When deduplicating: the same file:line CAN legitimately appear in both audits (e.g., an `onClick` that calls `fetch().catch(() => {})` is both an empty-handler safe-fail AND a happy-path stub if it's also missing the success branch). In that case, combine into one entry and tag both sources.

### 6. Return to the orchestrator

Brief summary (under 200 words):
- Total HIGH / MEDIUM / LOW counts.
- Top 3 HIGH items with file:line.
- Path to combined report.
- Any items from one audit that the other "could have caught but didn't" — useful for tuning.

## Output format philosophy

**Both source audits' classifications mean the same thing:**
- HIGH = user sees a broken affordance, or believes the action succeeded when it didn't. Block before ship.
- MEDIUM = real concern documented in code (TODO, stale workaround) but doesn't currently lie to the user.
- LOW = cosmetic markers, defensive defaults, intentional safe-fails with explanatory comments.
- FALSE-POSITIVE / NONE-INTENTIONAL = pattern matches but is correct behavior (e.g., `console.error` in a failure branch IS legitimate logging).

If the two specialists disagree on severity for the same site, use the higher severity in the aggregated report and note the disagreement.

## Anti-patterns (don't do these)

- Don't merge silent-failure-hunter's checklist with stub-audit's into a single prompt. Run them as separate specialists — the framing matters.
- Don't skip `silent-failure-hunter` because you "already swept for empty catches with grep." The agent's value is in judging the UX impact, not in pattern-matching.
- Don't author or modify Hebrew/i18n strings as part of this audit — flag them for separate review.
- Don't run before the prerequisite check (step 3) — the user's session won't have `silent-failure-hunter` unless the plugin is installed.

## Related skills / agents

- `stub-audit` — invoked by step 4 above. Can also be run standalone.
- `silent-failure-hunter` — invoked by step 4 above. Can also be run standalone via Task.
- `pr-review-toolkit:review-pr` slash command — different orchestrator, PR-scoped, runs 6 specialists. Use that for PR-context reviews; use this skill for full-codebase or branch-diff sweeps.
