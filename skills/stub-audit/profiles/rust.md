# Rust profile

Catches stubs and dead code in Rust projects (`Cargo.toml` present). Uses `cargo clippy` with the `dead_code` warning escalated, then layers Rust-specific greps for `todo!()`, `unimplemented!()`, `panic!("not implemented")`, and suspicious `#[allow(dead_code)]` attributes on items that should be reachable.

## Detection bash

```bash
# Clippy with dead_code escalated to warning level
cargo clippy --all-targets --workspace -- -W dead_code 2> /tmp/stub-audit-clippy.txt || true

# Explicit Rust stub macros
rg -n \
  -e '\btodo!\s*\(' \
  -e '\bunimplemented!\s*\(' \
  --glob '*.rs' --glob '!**/target/**' --glob '!**/tests/**' \
  || true

# panic!("not implemented") — common manual variant
rg -n \
  -e 'panic!\s*\(\s*["\'](not implemented|TODO|todo|unimplemented|stub|placeholder)' \
  --glob '*.rs' --glob '!**/target/**' --glob '!**/tests/**' \
  || true

# Empty function bodies (concrete fn, not trait declarations)
rg -n --multiline --multiline-dotall \
  -e 'fn\s+[a-zA-Z_][a-zA-Z0-9_]*\s*(<[^>]+>)?\s*\([^)]*\)(\s*->\s*[^{]+)?\s*\{\s*\}' \
  --glob '*.rs' --glob '!**/target/**' --glob '!**/tests/**' \
  || true

# #[allow(dead_code)] on items in non-test modules — these often mark forgotten stubs
rg -n -B1 \
  -e '#\[allow\(dead_code\)\]' \
  --glob '*.rs' --glob '!**/target/**' --glob '!**/tests/**' \
  || true

# TODO/FIXME markers in source
rg -n -i \
  -e '//\s*(TODO|FIXME|XXX|HACK)' \
  --glob '*.rs' --glob '!**/target/**' --glob '!**/tests/**' \
  || true

# Axum / Actix handlers returning hardcoded placeholder JSON
rg -n \
  -e 'Json\(\s*serde_json::json!\(\s*\{[^}]*(mock|fake|sample|placeholder|TODO|todo)' \
  --glob '*.rs' --glob '!**/target/**' --glob '!**/tests/**' \
  || true
```

Notes:

- `todo!()` and `unimplemented!()` are the canonical Rust stub macros. Their presence in a user-reachable code path is almost always HIGH — they panic at runtime, so the user does not see a silent stub but a crashed request.
- `cargo clippy` requires a buildable crate. If the build is broken, clippy fails before its lints run; greps cover the high-value cases without it.
- `#[allow(dead_code)]` is sometimes legitimate (FFI types, conditional features) — never flag the attribute alone; check whether the symbol is actually referenced from a reachable path.

## Always-skip patterns (Rust specific)

- Trait method declarations without a default body — `fn foo(&self);` is the trait contract, not a stub.
- Empty `impl` blocks — `impl Marker for T {}` is the marker-trait pattern.
- Test modules — anything under `#[cfg(test)] mod tests { ... }` or in `tests/` integration test directories.
- `unimplemented!()` inside `#[cfg(feature = "...")]` blocks that are off by default — these are intentional gates, not user-visible lies.
- `todo!()` inside a `#[doc(hidden)]` or `pub(crate)` helper that no public API exposes (still worth flagging as MEDIUM, since it is debt).
- `#[allow(dead_code)]` on FFI bindings (`extern "C"` blocks) and platform-conditional code.

## Graceful degradation

| Tool missing      | Lost                          | Fallback                                                                              |
| ----------------- | ----------------------------- | ------------------------------------------------------------------------------------- |
| `cargo` / `rustc` | clippy dead-code analysis     | Greps still surface every `todo!()` / `unimplemented!()` — the highest-value signal.  |

Install Rust via https://rustup.rs/. Without `cargo`, the audit still catches the explicit stub macros, which historically account for the majority of Rust user-visible stubs.
