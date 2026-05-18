# TypeScript / JavaScript profile

Catches stubs and dead code in node-shaped projects (TS, JS, MJS, CJS). Uses `knip` for dead-code/unused-exports and `leasot` for TODO/FIXME/XXX/HACK markers, then layers stack-level greps for explicit unimplemented throws and stub-named variables.

Framework-level UI patterns (empty `onClick`, no-op `@click` bindings) live in `frameworks/react.md`, `frameworks/vue.md`, `frameworks/svelte.md`, `frameworks/solidjs.md` and are loaded on top of this profile when the matching dependency is detected in `package.json`.

## Detection bash

```bash
# Dead code: unused files, exports, deps, class members
npx --yes knip --reporter json > /tmp/stub-audit-knip.json 2>/dev/null || true

# TODO/FIXME/XXX/HACK index across TS/JS sources
npx --yes leasot --reporter json \
  'app/**/*.{ts,tsx,js,jsx,mjs,cjs}' \
  'src/**/*.{ts,tsx,js,jsx,mjs,cjs}' \
  'pages/**/*.{ts,tsx,js,jsx,mjs,cjs}' \
  'components/**/*.{ts,tsx,js,jsx,mjs,cjs}' \
  'lib/**/*.{ts,tsx,js,jsx,mjs,cjs}' \
  'server/**/*.{ts,tsx,js,jsx,mjs,cjs}' \
  'hooks/**/*.{ts,tsx,js,jsx,mjs,cjs}' \
  'utils/**/*.{ts,tsx,js,jsx,mjs,cjs}' \
  'actions/**/*.{ts,tsx,js,jsx,mjs,cjs}' \
  'api/**/*.{ts,tsx,js,jsx,mjs,cjs}' \
  'routes/**/*.{ts,tsx,js,jsx,mjs,cjs}' \
  > /tmp/stub-audit-leasot.json 2>/dev/null || true

# Explicit unimplemented throws in user-reachable paths
rg -n -i \
  -e "throw new Error\(['\"](not implemented|todo|unimplemented|stub|placeholder)" \
  --glob '*.ts' --glob '*.tsx' --glob '*.js' --glob '*.jsx' --glob '*.mjs' --glob '*.cjs' \
  --glob '!**/*.test.*' --glob '!**/node_modules/**' \
  || true

# Stub-named variables in non-test files
rg -n \
  -e '\b(mock|fake|dummy|sample|stub)[A-Z][A-Za-z0-9_]*\s*[:=]' \
  --glob '*.ts' --glob '*.tsx' --glob '*.js' --glob '*.jsx' --glob '*.mjs' --glob '*.cjs' \
  --glob '!**/*.test.*' --glob '!**/vitest.setup.*' --glob '!**/test/**' --glob '!**/__tests__/**' \
  || true

# Empty function bodies in non-test files (noisy — manual filter required)
rg -n \
  -e 'function [a-zA-Z_][a-zA-Z0-9_]*\([^)]*\)\s*\{\s*\}' \
  -e '=>\s*\{\s*\}' \
  --glob '*.ts' --glob '*.tsx' --glob '*.js' --glob '*.jsx' --glob '*.mjs' --glob '*.cjs' \
  --glob '!**/*.test.*' --glob '!**/vitest.setup.*' \
  || true

# Commented-out implementation blocks with no replacement nearby
rg -n \
  -e '^\s*//\s*(await |const |return |if \(|fetch\()' \
  --glob '*.ts' --glob '*.tsx' --glob '*.js' --glob '*.jsx' --glob '*.mjs' --glob '*.cjs' \
  --glob '!**/*.test.*' | head -50 || true

# Hardcoded canned data in route handlers (Next.js App Router shape; generalize as needed)
rg -n --glob 'app/api/**/route.{ts,js}' -e 'return NextResponse\.json\(\s*\{[^}]*(mock|fake|sample|placeholder|TODO)' || true
```

Notes:

- `npx --yes` keeps the skill zero-install. If a project already pins `knip` or `leasot`, that pinned version runs.
- On WSL, `npx` sometimes errors with `UNC paths are not supported. Defaulting to Windows directory.` when the cwd is under `.claude/worktrees/`. If that happens, `cd` to the main worktree first or invoke from the project root explicitly. The grep sweep has no such constraint.
- If a shell wrapper (e.g., an `rg`-to-`grep` alias) intercepts `rg` and fails on `--glob`, call ripgrep by its absolute path (`/usr/bin/rg` on Debian/Ubuntu, `/opt/homebrew/bin/rg` on macOS) to bypass.
- `knip` reads `package.json` + `tsconfig.json` automatically; no config required for a first pass. If the project has a `knip.json`, it will be honored.
- If `knip` errors on first run (it often complains about missing Next.js/Supabase plugins or unconfigured entry points), do not stop. Decide if the error is structural (wrong entry points may need a one-line `knip.json` with `"entry": ["app/**/page.tsx", "app/**/route.ts", "app/**/layout.tsx"]` for a Next App Router project) or cosmetic. If cosmetic, fall back to `npx --yes knip --no-progress 2>&1 | head -200` and parse the text report.

## Always-skip patterns (TS/JS specific)

- TypeScript empty interfaces / empty type aliases used as branding: `interface Brand {}`, `type X = {}`. These are language idioms, not stubs.
- `Object.freeze({})` exports used as registry placeholders that consumers extend.
- Empty `useEffect(() => {}, [deps])` is a real anti-pattern but classify under `frameworks/react.md` to keep judgment consistent.
- `void 0` and `undefined` return literals in narrow generic helpers — these are language plumbing.

## Graceful degradation

Toolchain absent → coverage:

| Tool missing      | Lost                                  | Fallback                                                                  |
| ----------------- | ------------------------------------- | ------------------------------------------------------------------------- |
| `node` / `npx`    | knip (unused exports), leasot (TODOs) | Greps still run. Manually scan for `TODO`/`FIXME` with `rg -n -i todo`.   |
| `ripgrep` (`rg`)  | Fast grep sweep                       | Fall back to `grep -rn --include='*.ts' --include='*.tsx' <pattern> .`.   |

If `node` is missing entirely, this profile reports a degraded-coverage warning in the audit's Coverage notes section and proceeds with greps only.
