#!/usr/bin/env bash
# Mechanical-sweep regression harness.
#
# For each fixture under tests/fixtures/<fixture-name>/:
#   1. Read expected.json (file path + pattern label + min severity)
#   2. Run the matching profile's grep against the fixture root
#   3. Assert the expected file path appears in the grep output
#
# The profile-equivalent greps below mirror the regexes shipped in
# skills/stub-audit/profiles/*.md. If a profile's regex regresses, the
# corresponding entry will fail to surface here.
#
# The judgment pass (model classifies HIGH/MEDIUM/LOW) is out of scope —
# this harness only ensures the mechanical layer does not regress.
#
# Exit 0 on full hit. Exit 1 with a clear failure listing on miss.

set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required to parse expected.json manifests." >&2
  exit 2
fi

# Resolve repo root from this script's location so the harness works regardless of cwd.
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/.." && pwd)
fixtures_root="$repo_root/tests/fixtures"

if [ ! -d "$fixtures_root" ]; then
  echo "ERROR: $fixtures_root not found." >&2
  exit 2
fi

# Run the profile-equivalent grep for a given pattern label inside a fixture directory.
# Returns the list of files that match (one per line, relative to the fixture root).
#
# Mirror of the rg patterns in skills/stub-audit/profiles/*.md, expressed as
# grep -E (POSIX extended regex) so the harness has no ripgrep dependency.
run_profile_grep() {
  local fixture_dir="$1"
  local pattern="$2"

  case "$pattern" in
    # React framework profile, frameworks/react.md
    "onClick={() => {}}")
      grep -rEl --include='*.tsx' --include='*.jsx' \
        --exclude-dir=node_modules --exclude='*.test.*' \
        'onClick=\{\(\) => \{[[:space:]]*\}\}' "$fixture_dir" 2>/dev/null || true
      ;;

    # TypeScript profile — typescript.md (hardcoded canned data in route handlers).
    # Multi-line match: NextResponse.json({...mock|fake|sample|placeholder|TODO...}).
    "mock-data")
      python3 - "$fixture_dir" <<'PY' || true
import os, re, sys
root = sys.argv[1]
pat = re.compile(r'return\s+NextResponse\.json\(\s*\{[^}]*(mock|fake|sample|placeholder|TODO)', re.DOTALL)
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in {"node_modules", ".next", "dist", "build"}]
    for fn in filenames:
        if fn not in {"route.ts", "route.js"}:
            continue
        p = os.path.join(dirpath, fn)
        try:
            with open(p) as fh:
                src = fh.read()
        except OSError:
            continue
        if pat.search(src):
            print(p)
PY
      ;;

    # Python profile, explicit unimplemented raises.
    # Mirrors python.md globs (!**/tests/**, !**/test_*.py, !**/*_test.py) and
    # ruby.md globs (!**/spec/**, !**/test/**, !**/vendor/**).
    "raise NotImplementedError")
      grep -rEln --include='*.py' --include='*.rb' \
        --exclude-dir=tests --exclude-dir=test --exclude-dir=spec --exclude-dir=vendor \
        --exclude='test_*.py' --exclude='*_test.py' \
        'raise[[:space:]]+NotImplementedError' "$fixture_dir" 2>/dev/null | cut -d: -f1 || true
      ;;

    # Python profile — bare-pass function body
    # def name(...): \n pass
    "def charge")
      # Match concrete def with bare pass or ellipsis body.
      python3 - "$fixture_dir" <<'PY' || true
import os, re, sys
root = sys.argv[1]
pat = re.compile(r'def\s+[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*\)\s*(->\s*[^:]+)?:\s*\n\s*(pass|\.\.\.)\s*\n')
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in {"tests", ".venv", "venv", "__pycache__"}]
    for fn in filenames:
        if not fn.endswith(".py"):
            continue
        p = os.path.join(dirpath, fn)
        try:
            with open(p) as fh:
                src = fh.read()
        except OSError:
            continue
        if pat.search(src):
            print(p)
PY
      ;;

    # Python / Ruby profile, hardcoded canned data in handler return.
    # Mirrors the `return\s*\{[^}]*(mock|fake|...|placeholder|TODO|todo)` grep
    # in python.md and (for plain string-literal returns) ruby.md's Sinatra rule.
    "placeholder-return")
      python3 - "$fixture_dir" <<'PY' || true
import os, re, sys
root = sys.argv[1]
# Python: dict-return with placeholder-flavored keys/values.
py_pat = re.compile(r'return\s*\{[^}]*(mock|fake|sample|placeholder|TODO|todo)', re.DOTALL)
# Ruby: bare placeholder string literal at start of a line (Sinatra route body).
rb_pat = re.compile(r'^\s*[\'\"](TODO|todo|placeholder|coming soon|not implemented)[\'\"]\s*$', re.MULTILINE)
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in {"node_modules", "vendor", "__pycache__", ".venv", "venv"}]
    for fn in filenames:
        p = os.path.join(dirpath, fn)
        try:
            with open(p) as fh:
                src = fh.read()
        except OSError:
            continue
        if fn.endswith(".py") and py_pat.search(src):
            print(p)
        elif fn.endswith(".rb") and rb_pat.search(src):
            print(p)
PY
      ;;

    # Go profile, panic("not implemented"). Mirrors go.md (!**/*_test.go, !**/vendor/**).
    'panic("not implemented")')
      grep -rEln --include='*.go' --exclude-dir=vendor --exclude='*_test.go' \
        'panic\("[^"]*(not implemented|TODO|todo|unimplemented|stub|placeholder)' "$fixture_dir" 2>/dev/null | cut -d: -f1 || true
      ;;

    # Rust profile, todo!() macro. Mirrors rust.md (!**/target/**, !**/tests/**).
    "todo!(")
      grep -rEln --include='*.rs' --exclude-dir=target --exclude-dir=tests \
        'todo!\s*\(' "$fixture_dir" 2>/dev/null | cut -d: -f1 || true
      ;;

    *)
      echo "ERROR: unknown pattern label: $pattern" >&2
      return 2
      ;;
  esac
}

total_fixtures=0
total_findings=0
failed_findings=0
failed_fixtures=0

for fixture_dir in "$fixtures_root"/*/; do
  fixture=$(basename "$fixture_dir")
  manifest="$fixture_dir/expected.json"

  if [ ! -f "$manifest" ]; then
    echo "SKIP [$fixture]: no expected.json"
    continue
  fi

  total_fixtures=$((total_fixtures + 1))
  fixture_failed=0

  while IFS=$'\t' read -r exp_file exp_pattern; do
    [ -z "$exp_file" ] && continue
    total_findings=$((total_findings + 1))

    target="$fixture_dir/$exp_file"
    if [ ! -f "$target" ]; then
      echo "FAIL [$fixture] $exp_file: file does not exist in fixture" >&2
      failed_findings=$((failed_findings + 1))
      fixture_failed=1
      continue
    fi

    # Run the actual profile-equivalent grep across the fixture and check
    # the expected file path appears in the result.
    matched_files=$(run_profile_grep "$fixture_dir" "$exp_pattern")
    expected_abs="$fixture_dir$exp_file"

    if printf '%s\n' "$matched_files" | grep -F -q -- "$expected_abs"; then
      echo "OK   [$fixture] $exp_file: profile grep for '$exp_pattern' surfaced the file"
    else
      echo "FAIL [$fixture] $exp_file: profile grep for '$exp_pattern' did NOT surface the file" >&2
      echo "       grep output was:" >&2
      printf '%s\n' "$matched_files" | sed 's/^/         /' >&2
      failed_findings=$((failed_findings + 1))
      fixture_failed=1
    fi
  done < <(python3 - "$manifest" <<'PY'
import json, sys
with open(sys.argv[1]) as fh:
    data = json.load(fh)
for f in data.get("expected_findings", []):
    print(f"{f['file']}\t{f['pattern']}")
PY
  )

  if [ "$fixture_failed" = 1 ]; then
    failed_fixtures=$((failed_fixtures + 1))
  fi
done

echo
echo "Summary: $total_fixtures fixtures, $total_findings expected findings, $failed_findings failures"

if [ "$failed_findings" = 0 ]; then
  echo "PASS: every profile's mechanical sweep surfaces every planted fixture finding."
  exit 0
else
  echo "FAIL: $failed_findings expected findings did not surface in $failed_fixtures fixtures."
  exit 1
fi
