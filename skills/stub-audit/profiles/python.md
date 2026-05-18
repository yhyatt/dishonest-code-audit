# Python profile

Catches stubs and dead code in Python projects (`pyproject.toml` / `setup.py` / `requirements.txt`). Uses `vulture` for dead-code analysis and `leasot` for TODO/FIXME markers, then layers Python-specific greps for `raise NotImplementedError`, no-op function bodies, and framework-shape stubs (FastAPI / Flask route handlers returning canned dicts, Django views returning placeholder strings).

## Detection bash

```bash
# Dead code: unused functions, imports, attributes
python3 -m vulture . --min-confidence 70 > /tmp/stub-audit-vulture.txt 2>/dev/null \
  || pipx run vulture . --min-confidence 70 > /tmp/stub-audit-vulture.txt 2>/dev/null \
  || true

# TODO/FIXME/XXX/HACK index. leasot supports Python.
npx --yes leasot --reporter json \
  '**/*.py' \
  > /tmp/stub-audit-leasot-python.json 2>/dev/null || true

# Explicit unimplemented raises
rg -n \
  -e 'raise NotImplementedError' \
  -e 'raise Exception\(["\x27](not implemented|todo|stub|placeholder)' \
  --glob '*.py' --glob '!**/test_*.py' --glob '!**/*_test.py' --glob '!**/tests/**' \
  || true

# Bare-pass function bodies (def name(...): pass with no docstring above)
# Excludes Protocol / ABC / abstract methods which legitimately use pass.
rg -n --multiline --multiline-dotall \
  -e 'def [a-zA-Z_][a-zA-Z0-9_]*\([^)]*\)\s*(->\s*[^:]+)?:\s*\n\s*pass\s*\n' \
  --glob '*.py' --glob '!**/test_*.py' --glob '!**/*_test.py' --glob '!**/tests/**' \
  || true

# Bare-... function bodies (Ellipsis placeholder pattern)
rg -n --multiline --multiline-dotall \
  -e 'def [a-zA-Z_][a-zA-Z0-9_]*\([^)]*\)\s*(->\s*[^:]+)?:\s*\n\s*\.\.\.\s*\n' \
  --glob '*.py' --glob '!**/test_*.py' --glob '!**/*_test.py' --glob '!**/tests/**' \
  --glob '!**/*.pyi' \
  || true

# FastAPI / Flask handlers returning canned literal dicts (TODO/placeholder/mock content)
rg -n \
  -e 'return\s*\{[^}]*(mock|fake|sample|placeholder|TODO|todo)' \
  --glob '*.py' --glob '!**/test_*.py' --glob '!**/*_test.py' --glob '!**/tests/**' \
  || true

# Django views with HttpResponse placeholder text
rg -n \
  -e 'HttpResponse\(["\x27](TODO|todo|placeholder|coming soon|not implemented)' \
  --glob '*.py' --glob '!**/test_*.py' --glob '!**/*_test.py' --glob '!**/tests/**' \
  || true

# Stub-named module-level names
rg -n \
  -e '^(mock|fake|dummy|sample|stub)_[a-z_][a-z0-9_]*\s*=' \
  --glob '*.py' --glob '!**/test_*.py' --glob '!**/*_test.py' --glob '!**/tests/**' --glob '!**/conftest.py' \
  || true
```

Notes:

- `vulture` reports both dead code and unused imports. Filter against `# noqa` comments and `__all__` exports before reporting.
- `leasot` understands Python comments (`# TODO`, `# FIXME`) when given `.py` globs.
- The bare-`pass` pattern is noisy on `Protocol` / `ABC` / `@abstractmethod`. Always check the surrounding decorator context before classifying as HIGH. A `@abstractmethod` with `pass` is legitimate.

## Always-skip patterns (Python specific)

- `@abstractmethod` / `@abc.abstractmethod` definitions with `pass` or `...`. These are interface declarations, not stubs.
- `Protocol` subclasses with `...` bodies (PEP 544 structural interfaces).
- `@overload`-decorated stubs (PEP 484). The real implementation is later in the file.
- `pass` inside an `except:` block when the exception is genuinely ignorable (look for explanatory comment; if absent, flag as silent-failure candidate, not stub-audit).
- Type stubs in `.pyi` files: all bodies are `...` by convention.
- `NotImplementedError` raised inside an `@abstractmethod` body.
- `if TYPE_CHECKING:` blocks containing only imports.

## Graceful degradation

| Tool missing | Lost                                | Fallback                                                                                     |
| ------------ | ----------------------------------- | -------------------------------------------------------------------------------------------- |
| `vulture`    | Dead-code detection                 | Greps still surface explicit stubs (`raise NotImplementedError`, bare `pass` / `...`).       |
| `node`/`npx` | leasot TODO scan                    | Fallback grep: `rg -n -i -e '# (TODO\|FIXME\|XXX\|HACK)' --glob '*.py'`.                     |

Install `vulture` with `pipx install vulture` (recommended) or `pip install --user vulture`. If neither is available, the profile proceeds with greps only and notes the gap in Coverage notes.
