# Ruby profile

Catches stubs and dead code in Ruby projects (`Gemfile` present). Uses `rubocop`'s `Lint/UnreachableCode` cop, then layers Ruby-specific greps for `raise NotImplementedError`, empty Rails controller actions, and ERB templates with placeholder copy.

## Detection bash

```bash
# Rubocop's UnreachableCode lint
bundle exec rubocop --only Lint/UnreachableCode --format json > /tmp/stub-audit-rubocop.json 2>/dev/null \
  || rubocop --only Lint/UnreachableCode --format json > /tmp/stub-audit-rubocop.json 2>/dev/null \
  || true

# Explicit unimplemented raises
rg -n \
  -e 'raise NotImplementedError' \
  -e 'raise.*?["\'](not implemented|todo|stub|placeholder)' \
  --glob '*.rb' --glob '!**/spec/**' --glob '!**/test/**' --glob '!**/vendor/**' \
  || true

# Empty method bodies — def name(...) end with nothing in between
rg -n --multiline --multiline-dotall \
  -e 'def\s+[a-zA-Z_][a-zA-Z0-9_]*[?!=]?(\s*\([^)]*\))?\s*\n\s*end\b' \
  --glob '*.rb' --glob '!**/spec/**' --glob '!**/test/**' --glob '!**/vendor/**' \
  || true

# Rails controller actions that only call render with placeholder text
rg -n \
  -e 'render\s+(plain|text|json|html):\s*["\'](TODO|todo|placeholder|coming soon|not implemented)' \
  --glob '*.rb' --glob '!**/spec/**' --glob '!**/test/**' --glob '!**/vendor/**' \
  || true

# Sinatra route handlers returning a placeholder string literal
rg -n -B1 \
  -e '^\s*["\'](TODO|todo|placeholder|coming soon|not implemented)["\']\s*$' \
  --glob '*.rb' --glob '!**/spec/**' --glob '!**/test/**' --glob '!**/vendor/**' \
  || true

# ERB templates with placeholder copy outside of comments
rg -n \
  -e '(TODO|FIXME|XXX|HACK|Coming soon|Lorem ipsum|placeholder)' \
  --glob '*.erb' --glob '!**/spec/**' --glob '!**/test/**' --glob '!**/vendor/**' \
  || true

# TODO/FIXME markers in source
rg -n -i \
  -e '#\s*(TODO|FIXME|XXX|HACK)' \
  --glob '*.rb' --glob '!**/spec/**' --glob '!**/test/**' --glob '!**/vendor/**' \
  || true
```

Notes:

- `bundle exec rubocop` is preferred when the project pins rubocop in its Gemfile; otherwise the bare `rubocop` falls back to a globally-installed gem.
- Empty Ruby method bodies (`def foo; end` or `def foo\nend`) are unambiguous — Ruby has no abstract-method concept that uses an empty body. Compare with Python where `pass` is shared with `@abstractmethod`.
- ERB templates are surfaced explicitly because Rails projects often ship placeholder copy in `.erb` partials that escape every Ruby-source-only scan.

## Always-skip patterns (Ruby specific)

- Empty controller actions in a Rails generator scaffold that legitimately render a corresponding view template — check whether `app/views/<controller>/<action>.html.erb` exists. If the template renders real content, the empty action is the Rails convention.
- `raise NotImplementedError` inside a base class that is explicitly documented as "subclasses must override" — judge the call site, not the declaration.
- Stub gems in `spec/support/` or `test/support/`.
- `puts "TODO"` lines inside `lib/tasks/*.rake` files used for one-off scripts.
- `Class.new` blocks defining anonymous test doubles.

## Graceful degradation

| Tool missing       | Lost                            | Fallback                                                                                |
| ------------------ | ------------------------------- | --------------------------------------------------------------------------------------- |
| `bundle` / `ruby`  | rubocop lints                   | Greps still surface explicit `raise NotImplementedError` and empty-method patterns.     |
| `rubocop`          | UnreachableCode lint            | Same as above.                                                                          |

Install Ruby via `rbenv` or `asdf`. Install rubocop with `gem install rubocop` or by adding it to the project's Gemfile. The mechanical sweep produces useful candidates without the toolchain.
