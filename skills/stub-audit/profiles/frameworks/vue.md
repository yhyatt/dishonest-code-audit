# Vue framework profile

Layers on top of `typescript.md`. Catches Vue-specific UI-affordance stubs: empty `@click` bindings, empty methods in Options API, no-op `v-on:` handlers.

Detected when `package.json` lists `"vue"` as a dependency.

## Detection bash

```bash
# Empty @click / @submit / @change / v-on bindings — single-quote and double-quote variants
rg -n \
  -e '@click=["\x27]\(\)\s*=>\s*\{\s*\}["\x27]' \
  -e '@submit=["\x27]\(\)\s*=>\s*\{\s*\}["\x27]' \
  -e '@change=["\x27]\(\)\s*=>\s*\{\s*\}["\x27]' \
  -e 'v-on:click=["\x27]\(\)\s*=>\s*\{\s*\}["\x27]' \
  --glob '*.vue' --glob '!**/*.test.*' --glob '!**/node_modules/**' \
  || true

# Empty inline expression — @click=""
rg -n \
  -e '@click=""' \
  -e '@submit=""' \
  -e 'v-on:click=""' \
  --glob '*.vue' --glob '!**/*.test.*' \
  || true

# Options API methods with empty bodies — methods: { foo() {} } or foo: function() {}
rg -n --multiline --multiline-dotall \
  -e '[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*\{\s*\}\s*,' \
  --glob '*.vue' --glob '!**/*.test.*' \
  || true

# Methods that are bound in the template but defined as a no-op arrow in setup()
rg -n \
  -e 'const\s+[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*\(\)\s*=>\s*\{\s*\}' \
  --glob '*.vue' --glob '!**/*.test.*' \
  || true

# Computed properties returning a hardcoded placeholder
rg -n \
  -e 'computed\(\(\)\s*=>\s*["\x27](TODO|todo|placeholder|coming soon)' \
  --glob '*.vue' --glob '!**/*.test.*' \
  || true
```

## Always-skip patterns (Vue specific)

- `<form @submit.prevent="onSubmit">` where `onSubmit` is defined separately. The `.prevent` modifier is a no-op default-prevention shortcut, not a stub.
- Empty methods that exist purely to satisfy a parent's slot scope contract.
- Storybook (`*.stories.{ts,js}`) component definitions with no-op handlers.
- Methods named explicitly `noop` or `empty` and documented as deliberate no-ops.

## Worked examples (HIGH severity patterns)

1. **Labelled button with empty `@click`**

   ```vue
   <button @click="() => {}">שיתוף תוצאות</button>
   ```

2. **Method bound in template but defined as a no-op in setup**

   ```vue
   <template>
     <button @click="onAbandon">Abandon</button>
   </template>
   <script setup>
   const onAbandon = () => {}; // TODO: wire to API
   </script>
   ```

## Graceful degradation

Grep-only profile; no toolchain dependency beyond `ripgrep` (with `grep` as fallback).
