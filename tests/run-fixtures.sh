#!/usr/bin/env bash
# Mechanical-sweep regression harness.
#
# For each fixture under tests/fixtures/<fixture-name>/:
#   1. Read expected.json
#   2. For each expected_findings entry, verify the fixture file exists
#   3. Verify the listed pattern (or its mechanical-sweep equivalent) is present in that file
#
# The judgment pass (model classifies HIGH/MEDIUM/LOW) is out of scope — this harness
# only ensures the mechanical layer does not regress: the patterns the profiles look
# for must still be reachable in each fixture.
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

# Map "pattern label" -> grep search expression.
# These mirror the mechanical-sweep regexes in the profile files, simplified for
# fixed-string matching where the language pattern is unambiguous.
pattern_to_search() {
  case "$1" in
    "onClick={() => {}}")        echo 'onClick={() => {}}' ;;
    "mock-data")                 echo 'mock-data' ;;
    "toast-in-catch")            echo '.catch' ;;
    "raise NotImplementedError") echo 'raise NotImplementedError' ;;
    "def charge")                echo 'def charge' ;;
    'panic("not implemented")')  echo 'panic("not implemented")' ;;
    "todo!(")                    echo 'todo!(' ;;
    *)                           echo "$1" ;;
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

  # Use python3 to extract (file, pattern) pairs deterministically.
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

    search=$(pattern_to_search "$exp_pattern")
    if ! grep -F -q -- "$search" "$target"; then
      echo "FAIL [$fixture] $exp_file: pattern '$exp_pattern' not found (searched for: '$search')" >&2
      failed_findings=$((failed_findings + 1))
      fixture_failed=1
      continue
    fi

    echo "OK   [$fixture] $exp_file: '$exp_pattern' found"
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
  echo "PASS: all mechanical-sweep patterns surface in their fixtures."
  exit 0
else
  echo "FAIL: $failed_findings expected findings did not surface in $failed_fixtures fixtures."
  exit 1
fi
