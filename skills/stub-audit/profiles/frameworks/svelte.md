# Svelte framework profile

Layers on top of `typescript.md`. Catches Svelte-specific UI-affordance stubs: empty `on:click` bindings, no-op functions in `<script>` blocks, empty exports.

Detected when `package.json` lists `"svelte"` as a dependency.

## Detection bash

```bash
# Empty on:click / on:submit / on:change bindings
rg -n \
  -e 'on:click=\{\(\)\s*=>\s*\{\s*\}\}' \
  -e 'on:submit=\{\(\)\s*=>\s*\{\s*\}\}' \
  -e 'on:change=\{\(\)\s*=>\s*\{\s*\}\}' \
  --glob '*.svelte' --glob '!**/*.test.*' --glob '!**/node_modules/**' \
  || true

# Empty function in <script> tied to an event
rg -n \
  -e 'function\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*\{\s*\}' \
  --glob '*.svelte' --glob '!**/*.test.*' \
  || true

# Empty arrow assigned to a let/const that ends up bound in markup
rg -n \
  -e 'let\s+[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*\(\)\s*=>\s*\{\s*\}' \
  -e 'const\s+[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*\(\)\s*=>\s*\{\s*\}' \
  --glob '*.svelte' --glob '!**/*.test.*' \
  || true

# Empty exports — `export let foo;` followed by no consumption
rg -n \
  -e 'export\s+let\s+[a-zA-Z_][a-zA-Z0-9_]*\s*;' \
  --glob '*.svelte' --glob '!**/*.test.*' \
  || true

# +page.server.ts / +server.ts actions returning placeholder data (SvelteKit)
rg -n \
  -e 'return\s*\{[^}]*(mock|fake|sample|placeholder|TODO|todo)' \
  --glob '+server.ts' --glob '+server.js' --glob '+page.server.ts' --glob '+page.server.js' \
  || true
```

## Always-skip patterns (Svelte specific)

- `export let foo;` props that are forwarded down to a child component via `<Child {foo} />` — the parent component does not consume the prop directly, but the binding is real.
- Empty `<script>` blocks in markup-only components.
- SvelteKit `+layout.ts` files that exist purely to set `prerender = true` and have no other logic.
- Bind directives (`bind:value={...}`) that route through a no-op-looking handler in a controlled-component pattern.

## Worked examples (HIGH severity patterns)

1. **Labelled button with empty `on:click`**

   ```svelte
   <button on:click={() => {}}>Share results</button>
   ```

2. **Function declared in `<script>`, bound in markup, body is empty**

   ```svelte
   <script>
     function onAbandon() {} // TODO: wire later
   </script>
   <button on:click={onAbandon}>Abandon</button>
   ```

## Graceful degradation

Grep-only profile; no toolchain dependency beyond `ripgrep` (with `grep` as fallback).
