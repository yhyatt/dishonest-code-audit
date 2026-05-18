---
name: stub-audit
description: Audit a codebase for mock, stub, placeholder, or TODO code that lives in a real user-visible path (buttons that do nothing, hand-drawn placeholder SVGs that ignore their input, handlers that don't call the server, stale TODOs on shipped slices, hardcoded canned data in route handlers). Wraps knip + leasot + a tuned grep sweep to build a candidate list, then uses the model to judge each one against the question "does the user see this and does it lie to them?" Use whenever the user asks for a mock/stub/placeholder audit, a "what's fake in this codebase" pass, a stale-TODO sweep, a pre-release sanity check for unfinished work, or before shipping/cutting a release. Also use proactively at the end of a slice or before merging a feature branch. Output goes to a fresh `MOCK-STUB-AUDIT.md` modeled on `.slice-13-prep/MOCK-STUB-AUDIT.md`.
---

# stub-audit

Find mock/stub/placeholder code that ships to users in a real code path, separate it from intentional patterns that look like stubs but are not, and produce a report a human can act on in one sitting.

The bug this skill protects against is the **broken-affordance** bug: a button whose `onClick` is `() => {}`, a "QR code" that is a hand-drawn SVG ignoring its input prop, a "share" action that opens nothing, an "abandon session" that updates no server state. Static analysis cannot tell you whether these matter. The model can — *if* you give it the right candidate list and the right judgment lens.

## Methodology (three phases)

### Phase 1 — Mechanical sweep

Run two zero-setup tools to produce the bulk of the candidate list. They are noisy on purpose; we filter later.

```bash
# Dead code: unused files, exports, deps, class members
npx --yes knip --reporter json > /tmp/stub-audit-knip.json 2>/dev/null || true

# TODO/FIXME/XXX/HACK index
npx --yes leasot --reporter json \
  'app/**/*.{ts,tsx}' \
  'components/**/*.{ts,tsx}' \
  'lib/**/*.{ts,tsx}' \
  'supabase/migrations/*.sql' \
  > /tmp/stub-audit-leasot.json 2>/dev/null || true
```

Notes:
- `npx --yes` keeps the skill zero-install. If a project already pins `knip` or `leasot`, that pinned version runs.
- On WSL, `npx` sometimes errors with `UNC paths are not supported. Defaulting to Windows directory.` when the cwd is under `.claude/worktrees/`. If that happens, `cd` to the main worktree first or invoke from the project root explicitly (`cd /home/<user>/projects/<repo> && npx --yes ...`). The grep sweep in Phase 2 has no such constraint and can run from anywhere.
- If a shell wrapper (e.g., `rtk`, an `rg`→`grep` alias) intercepts `rg` and fails on `--glob`, call ripgrep by its absolute path (`/usr/bin/rg` on Debian/Ubuntu, `/opt/homebrew/bin/rg` on macOS) to bypass.
- `knip` reads `package.json` + `tsconfig.json` automatically; no config required for a first pass. If the project has a `knip.json`, it will be honored.
- If `knip` errors on first run (common — it complains about missing Next.js/Supabase plugins or unconfigured entry points), do not stop. Read the error, decide if it's structural (wrong entry points → may need a one-line `knip.json` with `"entry": ["app/**/page.tsx", "app/**/route.ts", "app/**/layout.tsx"]` for a Next App Router project) or cosmetic. If cosmetic, fall back to `npx --yes knip --no-progress 2>&1 | head -200` and parse the text report. Do not block the audit on knip config.
- Tune the leasot globs to the project's layout. Defaults above match a Next.js App Router project with a `lib/`, `components/`, and Supabase migrations. For a different layout, adjust.

### Phase 2 — Grep sweep for what knip + leasot miss

The most damaging stubs in production are not dead code and have no TODO marker. They are **live code that does nothing**. Cover them with targeted greps.

```bash
# Buttons / handlers wired to no-op closures (single-line form)
rg -n -e 'onClick=\{\(\) => \{\s*\}\}' \
  -e 'onSubmit=\{\(\) => \{\s*\}\}' \
  -e 'onChange=\{\(\) => \{\s*\}\}' \
  --glob '*.tsx' --glob '*.ts' --glob '!**/*.test.*' --glob '!**/node_modules/**'

# Multiline form — handler body contains only a comment (the classic "TODO: wire later" stub)
rg -n --multiline --multiline-dotall \
  -e 'onClick=\{\(\) => \{\s*//[^}]{0,200}\}\}' \
  -e 'onSubmit=\{\(\) => \{\s*//[^}]{0,200}\}\}' \
  --glob '*.tsx' --glob '!**/*.test.*' --glob '!**/node_modules/**'

# Explicit unimplemented throws in user-reachable paths
rg -n -i -t ts -t tsx \
  -e "throw new Error\(['\"](not implemented|todo|unimplemented|stub|placeholder)" \
  --glob '!**/*.test.*'

# Stub-named variables in non-test files
rg -n -t ts -t tsx \
  -e '\b(mock|fake|dummy|sample|stub)[A-Z][A-Za-z0-9_]*\s*[:=]' \
  --glob '!**/*.test.*' --glob '!**/vitest.setup.*' --glob '!**/test/**' --glob '!**/__tests__/**'

# Empty function bodies in non-test files (noisy — manual filter required)
rg -n -t ts -t tsx \
  -e 'function [a-zA-Z_][a-zA-Z0-9_]*\([^)]*\)\s*\{\s*\}' \
  -e '=>\s*\{\s*\}' \
  --glob '!**/*.test.*' --glob '!**/vitest.setup.*'

# Commented-out implementation blocks with no replacement nearby
rg -n -t ts -t tsx -e '^\s*//\s*(await |const |return |if \(|fetch\()' \
  --glob '!**/*.test.*' | head -50

# Hardcoded canned data in route handlers
rg -n --glob 'app/api/**/route.ts' -e 'return NextResponse\.json\(\s*\{[^}]*(mock|fake|sample|placeholder|TODO)'
```

Run these in parallel where possible. Concatenate the results to your candidate list. **None of these results is automatically a finding** — they are leads.

### Phase 3 — Judgment pass (this is where the model earns its keep)

For each candidate, open the surrounding 20–40 lines (use `Read` with `offset`/`limit`, or `find_symbol` + `get_function_source` from token-savior for symbol-level fetches in large files). Then answer four questions in order:

1. **Is this user-reachable?** Trace from an `app/` route or a top-level component. If it's behind a feature flag that is off, a dev-only branch (`process.env.NODE_ENV !== 'production'`), or in a file that no production entry imports, downgrade to LOW or FALSE-POSITIVE and note the gate.
2. **Does the user see a broken affordance, or does the code silently work?** A button labelled "שיתוף תוצאות" with `onClick={() => {}}` is HIGH. A no-op `onChange` on a controlled component whose state is also set elsewhere is FALSE-POSITIVE. The bar is: does the user expect something to happen, and does nothing happen?
3. **Does the stub lie to the user?** Toast says "saved!" but no API was called → HIGH. Caption says "scan or type the code" next to a non-functional QR → HIGH. Comment is honest about being a stub but the UI string is also a placeholder ("TBD") → MEDIUM, because the user is warned.
4. **Is the marker stale?** A `TODO(slice-12)` in a codebase where slice 12 has shipped and the item is not in `BACKLOG.md` is **MEDIUM minimum** even if the code path is dormant — stale markers rot. Check the project's plan/backlog files (`docs/BACKLOG.md`, `~/.claude/plans/*.md`, etc.) before classifying TODO markers; tracked TODOs are LOW, untracked TODOs on shipped milestones are MEDIUM.

### Classification

- **HIGH** — production code path with placeholder behavior. The user sees a broken or misleading affordance. Always include exact line, exact code, exact user-visible string (in the project's language — do not translate), and the smallest fix size you can estimate.
- **MEDIUM** — TODO/FIXME on a non-trivial real concern, or a stale marker on a shipped milestone. The code works today; the marker is debt or risk.
- **LOW** — cosmetic markers, intentional dev-only branches, documented `eslint-disable`. Keep the count, skip the prose.
- **FALSE-POSITIVE** — legitimate patterns that share shape with stubs. Examples below.

### Always-skip patterns (do not flag these)

The mechanical sweep will surface all of these. Filter them out before the report stage.

- `placeholder="..."` on `<input>` / `<textarea>` — these are HTML attributes for user-facing hint text, not stubs.
- JSDoc-style `null = not yet ...` semantic docs on nullable state types — `null` is a real value the consumer handles.
- `console.error(...)` in a failure branch of a user-facing flow — this is real error logging.
- `localhost:3000` / `127.0.0.1:3000` as the **last** fallback inside a `??` or `||` chain that prefers an env var or a forwarded header. Defensive default for dev, not a stub.
- `eslint-disable` / `eslint-disable-next-line` with a comment that documents the reason.
- Stub-shaped strings (`mockX`, `fakeX`, `dummyX`) inside test files, vitest setup, fixtures, or any path matched by `*.test.*`, `__tests__/`, `test/`, `fixtures/`.
- `mockImplementation`, `vi.mock`, `vi.fn()` in test setup files.
- React `useCallback` / `useEffect` deps lists that legitimately omit a stable handler (look for the `eslint-disable-next-line react-hooks/exhaustive-deps` marker with reason).
- TODOs that **are** tracked in `BACKLOG.md` or the active plan file with a target slice. These are LOW, not MEDIUM.

When in doubt, downgrade rather than upgrade. A false HIGH erodes the reader's trust in the rest of the report; a false LOW is recoverable next sweep.

## Report format

Always write to a fresh `MOCK-STUB-AUDIT.md` in the directory the invoking context wants (typically `.slice-XX-prep/` or `.slice-XX-review-mockstubs/`). If the caller does not specify, create `.stub-audit-<YYYY-MM-DD>/MOCK-STUB-AUDIT.md` at the repo root. Per ballpark's convention (and most projects'), `.<kind>-*` dirs are gitignored — confirm against `.gitignore` before writing if you care about cleanliness.

Use this exact skeleton — readers of this kind of report scan top-down and bail when the structure breaks.

```markdown
# Mock / Stub / Placeholder Audit

Scope: <which files were scanned, which were excluded, read-only or not>.

## Summary
- Total suspect sites found: <N>
- HIGH (active production code path that returns fake/canned data, throws, or is empty): <n>
- MEDIUM (real code with a TODO/FIXME marker on a non-trivial concern): <n>
- LOW (cosmetic TODO comments, intentional dev-only branches, etc.): <n>
- FALSE-POSITIVE (legitimate uses of these patterns): ~<n> (<one-line list of categories>)

Headline: <one sentence — what's NOT broken. e.g., "no auth-check stubs, no payment-like flows, no route handlers returning canned data">.

## HIGH (production code with placeholder behavior)

### <path/to/file.tsx>:<line-range> (`<symbol or affordance name>`)
- Pattern: <one-line label, e.g., mock-data, stub-return, empty-impl>
- Context: <where in the UX this sits, what the user expects>
- Evidence:
  ```ts
  <minimal code excerpt — enough for the reader to see the lie>
  ```
- Impact: <what the user experiences. Be specific. Reference the relevant AGENTS.md / engineering principle if the stub violates one>.
- Fix size: <trivial | small | real-work | unknown> (<one-line how>)

## MEDIUM (TODO/FIXME on real concerns)

### <path>:<line>
- Marker: `<exact comment text>`
- Context: <what the code does today vs what the marker promises>
- Concern: <why it matters / whether it's tracked in BACKLOG>
- Fix size: <trivial | small | real-work>

## LOW (cosmetic markers)

- `<path>:<line>` — <one-sentence note>
- ...

---

## What I deliberately did NOT flag

- <category 1 — e.g., "All `placeholder=` attrs on inputs">
- <category 2>
- ...
```

The "deliberately did NOT flag" section is load-bearing. It tells the reader the model saw the pattern and made a call, so they don't burn time re-running the audit thinking it missed things.

## Invocation hints

- The skill is most valuable at slice/PR boundaries, before a release, or when a human suspects "this thing looks finished but I'm not sure." Trigger words: "mock," "stub," "placeholder," "what's fake," "TODO sweep," "is anything not implemented," "pre-release audit."
- Time budget per audit on a ~50-file codebase: 5-10 minutes wall clock. Most of that is the judgment pass; the mechanical sweeps finish in seconds.
- Output is a Markdown file the human reads once and acts on. Do **not** auto-fix the findings — the value is the curated list with judgment, not the patch.

## Project-specific tuning (ballpark)

This skill was authored against the ballpark codebase. The shape of stubs we hit twice in production:
- Hand-drawn placeholder SVG that doesn't encode its `value` prop (`QRCodePlaceholder`).
- `onClick={() => {}}` on a `Button intent="secondary" size="lg"` that visually equals a real action button.
- `handleX` that opens a `confirm()` then `router.push`es without an API call, on a feature whose schema/RPC already supports the state transition.

When auditing ballpark, weight these patterns heavily in Phase 2. When auditing a different project, generalize: the question is always "does this affordance look real and behave fake?"

Reference audit: `/home/yonatan/projects/ballpark/.slice-13-prep/MOCK-STUB-AUDIT.md`.
