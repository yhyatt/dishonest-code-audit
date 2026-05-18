# dishonest-code-audit

Two parallel Claude Code skills that find code that misleads users.

## What it ships

- **`dishonest-code-audit`** — meta-orchestrator skill. Runs both audits below in parallel against a scope (whole codebase / branch diff / specific directory) and aggregates their findings into one combined report.
- **`stub-audit`** — standalone mock/stub/placeholder auditor. Wraps `npx --yes knip` + `npx --yes leasot` + a tuned grep sweep to build a candidate list, then uses LLM judgment to classify each finding by UX impact (HIGH / MEDIUM / LOW / FALSE-POSITIVE).

The meta-skill spawns two specialist sub-agents in parallel: `silent-failure-hunter` (for error paths) and a wrapped invocation of `stub-audit` (for happy paths). Keeping them as two specialists is intentional — silent-failure-hunter reasons about catch blocks and fallback logic; stub-audit reasons about empty handlers and placeholder data. Merging the prompts dilutes both judgments.

## Prerequisite — install pr-review-toolkit first

`dishonest-code-audit` invokes `silent-failure-hunter`, which is a sub-agent shipped by Anthropic's `pr-review-toolkit` plugin. Install it first:

```bash
claude plugin install pr-review-toolkit@claude-plugins-official
```

## Install

Once published to GitHub:

```bash
claude plugin install <owner>/dishonest-code-audit
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
- `<output-dir>/DISHONEST-CODE-AUDIT.md` (combined, deduplicated, written by the meta-skill)

Default `<output-dir>` is `.audit-<topic>/` at repo root, or `.slice-XX-prep/` if the project uses that convention.

## Classification

Both specialists use a shared severity model:

- **HIGH** — user sees a broken affordance, or believes the action succeeded when it didn't. Block before ship.
- **MEDIUM** — real concern documented in code (TODO, stale workaround) but doesn't currently lie to the user.
- **LOW** — cosmetic markers, defensive defaults, intentional safe-fails with explanatory comments.
- **FALSE-POSITIVE / NONE-INTENTIONAL** — pattern matches but is correct behavior.

If the two specialists disagree on severity for the same site, the combined report uses the higher severity and notes the disagreement.

## Provenance

Born from a real pre-ship audit of a Next.js + Supabase + TypeScript codebase. The audits caught:

- Two HIGH live-tournament correctness bugs (player submits answer, server returns 5xx, UI advances as if successful).
- Three MEDIUM clipboard liar-toasts (`'הועתק'` fires even when `writeText` rejected).
- One HIGH host-side "abandon session" handler that navigated away without telling the server.
- One HIGH hand-drawn SVG "QR code" that did not encode its `value` prop.
- One HIGH `שיתוף תוצאות` button with empty `onClick` and a stale `// TODO(slice-12)` marker.

All of those landed on `main` despite passing manual review.

## License

MIT.
