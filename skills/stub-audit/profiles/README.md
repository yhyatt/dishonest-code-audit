# Profiles

Stack-specific candidate generators for `stub-audit`. The main SKILL stays methodology-only; each profile here plugs in concrete tooling, grep patterns, and skip-lists for one language or UI framework.

## Layout

```
profiles/
  typescript.md      stack profile for JS/TS projects (node-shaped)
  python.md          stack profile for Python projects
  go.md              stack profile for Go projects
  rust.md            stack profile for Rust projects
  ruby.md            stack profile for Ruby projects
  frameworks/
    react.md         JSX patterns (loaded on top of typescript)
    vue.md           Vue SFC patterns (loaded on top of typescript)
    svelte.md        Svelte component patterns (loaded on top of typescript)
    solidjs.md       Solid JSX variant (loaded on top of typescript)
```

A stack profile owns: dead-code tool, TODO scanner, language-level grep patterns, always-skip patterns specific to that language. A framework profile owns UI-affordance patterns layered on top of a stack profile: empty handlers, placeholder components, no-op event bindings.

## How profiles are loaded

`stub-audit/SKILL.md` Phase 1 runs detection at the start:

```bash
PROFILES=()
[ -f package.json ]      && PROFILES+=("typescript")
[ -f pyproject.toml ] || [ -f setup.py ] || [ -f requirements.txt ] && PROFILES+=("python")
[ -f go.mod ]            && PROFILES+=("go")
[ -f Cargo.toml ]        && PROFILES+=("rust")
[ -f Gemfile ]           && PROFILES+=("ruby")

# Framework detection runs only after the typescript profile loaded
if [[ " ${PROFILES[*]} " =~ " typescript " ]]; then
  grep -q '"react"'    package.json 2>/dev/null && PROFILES+=("frameworks/react")
  grep -q '"vue"'      package.json 2>/dev/null && PROFILES+=("frameworks/vue")
  grep -q '"svelte"'   package.json 2>/dev/null && PROFILES+=("frameworks/svelte")
  grep -q '"solid-js"' package.json 2>/dev/null && PROFILES+=("frameworks/solidjs")
fi
```

If no profile matches, fall back to the generic patterns in `stub-audit/SKILL.md` (TODO/FIXME/HACK markers + empty-body regex) and warn the user that coverage will be thin.

## Profile file structure

Every profile file follows the same shape so the SKILL can read it predictably:

1. **Intro**: one or two sentences on what this profile catches.
2. **Detection bash**: the commands that produce the candidate list. Every command must tolerate a missing toolchain (`|| true` after the toolchain call, fall back to grep). Toolchain absence is not fatal.
3. **Always-skip patterns**: language-specific noise the mechanical sweep will produce that should never become a finding (idiomatic empty interfaces, language-level placeholder values, etc.).
4. **Graceful degradation**: what coverage looks like when the toolchain is missing, and what the user should install to lift it.

## Adding a new profile

See `CONTRIBUTING.md` at the repo root. The short version:

1. Copy the closest existing profile as a starting point.
2. Add a tiny fixture under `tests/fixtures/<your-stack>/` with at least one planted finding per pattern.
3. Add an `expected.json` manifest listing the file paths and pattern labels the mechanical sweep must surface.
4. Run `bash tests/run-fixtures.sh`. It must exit 0.
5. Document the toolchain dependency and graceful-fallback behavior in the profile file.
