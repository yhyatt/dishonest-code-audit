# React framework profile

Layers on top of `typescript.md`. Catches React-specific UI-affordance stubs: empty event handlers in JSX, placeholder components with prop signatures that ignore their inputs, no-op effects masquerading as wiring.

Detected when `package.json` lists `"react"` as a dependency.

## Detection bash

```bash
# Buttons / handlers wired to no-op closures (single-line form)
rg -n \
  -e 'onClick=\{\(\) => \{\s*\}\}' \
  -e 'onSubmit=\{\(\) => \{\s*\}\}' \
  -e 'onChange=\{\(\) => \{\s*\}\}' \
  -e 'onBlur=\{\(\) => \{\s*\}\}' \
  -e 'onFocus=\{\(\) => \{\s*\}\}' \
  --glob '*.tsx' --glob '*.jsx' --glob '!**/*.test.*' --glob '!**/node_modules/**' \
  || true

# Multiline form: handler body contains only a comment (the "TODO: wire later" stub)
rg -n --multiline --multiline-dotall \
  -e 'onClick=\{\(\) => \{\s*//[^}]{0,200}\}\}' \
  -e 'onSubmit=\{\(\) => \{\s*//[^}]{0,200}\}\}' \
  --glob '*.tsx' --glob '*.jsx' --glob '!**/*.test.*' --glob '!**/node_modules/**' \
  || true

# Empty useEffect / useCallback bodies (effect that does nothing but is wired up)
rg -n \
  -e 'useEffect\(\(\) => \{\s*\}' \
  -e 'useCallback\(\(\) => \{\s*\}' \
  --glob '*.tsx' --glob '*.jsx' --glob '!**/*.test.*' \
  || true

# Component definitions that accept a prop but never reference it (single-component file heuristic)
# This is intentionally narrow. Looks for "function Foo({ value }: ...)" or "({ value })" without "value" appearing later in the function body.
# Manual review still required; mechanical sweep just flags candidates.
rg -n --multiline --multiline-dotall \
  -e 'function [A-Z][A-Za-z0-9_]*\(\s*\{\s*value\s*\}[^)]*\)' \
  --glob '*.tsx' --glob '*.jsx' --glob '!**/*.test.*' \
  || true
```

## Always-skip patterns (React specific)

- `onChange={() => {}}` on a controlled component whose `value` is set elsewhere via state. The handler exists to satisfy React's controlled-component contract, not to do work. Verify by looking for a sibling `value={state.x}` and a separate update path.
- Storybook stories (`*.stories.tsx`) with no-op handlers. These are display-only fixtures.
- `<form onSubmit={(e) => e.preventDefault()}>` patterns where the work happens via a separate button handler. The empty-looking submit is intentional.
- React `useCallback(() => {}, [deps])` used as a stable identity placeholder passed to a child that conditionally calls it. Judge by usage, not by the empty body alone.
- Placeholder fallback UIs rendered only when an error boundary catches (`<ErrorFallback>...</ErrorFallback>`). These are recovery affordances, not stubs.

## Worked examples (HIGH severity patterns)

1. **Empty `onClick` on a labelled action button**

   ```tsx
   <Button onClick={() => {}}>שיתוף תוצאות</Button>
   // The button has a real label promising an action. Nothing happens.
   ```

2. **Hand-drawn placeholder SVG that ignores its `value` prop**

   ```tsx
   function QRCodePlaceholder({ value }: { value: string }) {
     return <svg>{/* literal QR-looking pixels, value never referenced */}</svg>;
   }
   ```

3. **Handler that navigates without notifying the server**

   ```tsx
   const onAbandon = () => {
     if (confirm("Abandon session?")) router.push("/");
     // No fetch / mutation. Server still thinks the session is live.
   };
   ```

## Graceful degradation

This profile is grep-only; it has no toolchain dependency beyond `ripgrep` (with `grep` as fallback). It is always available when the React stack is detected.
