# SolidJS framework profile

Layers on top of `typescript.md`. Catches Solid-specific UI-affordance stubs in JSX components. Most patterns mirror React because Solid uses JSX, but Solid's reactivity primitives (`createSignal`, `createEffect`, `createMemo`) introduce additional shapes worth scanning.

Detected when `package.json` lists `"solid-js"` as a dependency.

## Detection bash

```bash
# Empty event handlers (Solid uses on:click instead of onClick when targeting native events,
# but most apps use camelCase via the JSX runtime, so cover both forms)
rg -n \
  -e 'onClick=\{\(\)\s*=>\s*\{\s*\}\}' \
  -e 'onSubmit=\{\(\)\s*=>\s*\{\s*\}\}' \
  -e 'onInput=\{\(\)\s*=>\s*\{\s*\}\}' \
  -e 'on:click=\{\(\)\s*=>\s*\{\s*\}\}' \
  -e 'on:submit=\{\(\)\s*=>\s*\{\s*\}\}' \
  --glob '*.tsx' --glob '*.jsx' --glob '!**/*.test.*' --glob '!**/node_modules/**' \
  || true

# Empty createEffect / createMemo bodies
rg -n \
  -e 'createEffect\(\(\)\s*=>\s*\{\s*\}\)' \
  -e 'createMemo\(\(\)\s*=>\s*\{\s*\}\)' \
  --glob '*.tsx' --glob '*.jsx' --glob '*.ts' --glob '*.js' --glob '!**/*.test.*' \
  || true

# Signal setters that are exported and bound in markup but called with a no-op wrapper
rg -n \
  -e 'const\s*\[\s*[a-zA-Z_][a-zA-Z0-9_]*\s*,\s*set[A-Z][A-Za-z0-9_]*\s*\]\s*=\s*createSignal' \
  --glob '*.tsx' --glob '*.jsx' --glob '!**/*.test.*' \
  || true
```

## Always-skip patterns (SolidJS specific)

- `createEffect(() => track())` patterns where the effect's purpose is to subscribe a signal for reactivity — the body may look minimal but is doing real work via the signal call inside.
- `createMemo(() => value())` thin wrappers around a signal — legitimate idiom for stabilizing a computed reference.
- `<Show when={...} fallback={...}>` placeholder fallback content — judge by the fallback markup, not by the presence of a "placeholder" keyword.

## Worked examples (HIGH severity patterns)

1. **Empty `onClick` on a labelled action button**

   ```tsx
   <button onClick={() => {}}>Share results</button>
   ```

2. **Effect declared but does nothing**

   ```tsx
   createEffect(() => {
     // TODO: subscribe to room
   });
   ```

## Graceful degradation

Grep-only profile; no toolchain dependency beyond `ripgrep` (with `grep` as fallback).
