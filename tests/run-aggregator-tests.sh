#!/usr/bin/env bash
# Aggregator regression harness.
#
# For each fixture under tests/fixtures/aggregator/<case>/:
#   - safe-fail.md + mock-stub.md (+ optional known-clean.txt) are the inputs
#   - expected.json is a *partial* JSON spec; the harness asserts every key in
#     it (recursively) is present-and-equal in the produced AGGREGATE.json
#
# Special case: case-06-malformed asserts the aggregator EXITS NON-ZERO and
# stderr names both the offending source file path and a line number.
#
# The point of this harness is mechanical regression coverage of dedup,
# fuzzy-match, severity merge, and known-clean reclassification. The
# judgment-layer behavior (LLM filling placeholders) is out of scope.

set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required for the aggregator harness." >&2
  exit 2
fi

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd "$script_dir/.." && pwd)
aggregator="$repo_root/skills/dishonest-code-audit/lib/aggregate.py"
fixtures_root="$repo_root/tests/fixtures/aggregator"

if [ ! -f "$aggregator" ]; then
  echo "ERROR: aggregator not found at $aggregator" >&2
  exit 2
fi
if [ ! -d "$fixtures_root" ]; then
  echo "ERROR: $fixtures_root not found." >&2
  exit 2
fi

total_cases=0
failed_cases=0

# Compare a partial-expected JSON (subset) against an actual JSON file.
# Returns 0 on full subset-match, 1 with a diagnostic on mismatch.
assert_subset() {
  local expected_path="$1"
  local actual_path="$2"
  local case_name="$3"

  python3 - "$expected_path" "$actual_path" "$case_name" <<'PY'
import json, sys

expected_path, actual_path, case_name = sys.argv[1], sys.argv[2], sys.argv[3]
with open(expected_path) as f: expected = json.load(f)
with open(actual_path) as f: actual = json.load(f)

errors = []

def check_counts(exp, act, path):
    for k, v in exp.items():
        if k not in act:
            errors.append(f"{path}.{k}: missing in actual")
        elif act[k] != v:
            errors.append(f"{path}.{k}: expected {v!r}, got {act[k]!r}")

# 1. counts: strict per-key subset check.
if "counts" in expected:
    check_counts(expected["counts"], actual.get("counts", {}), "counts")

# 2. findings_count_min: lower bound on number of findings.
if "findings_count_min" in expected:
    actual_n = len(actual.get("findings", []))
    if actual_n < expected["findings_count_min"]:
        errors.append(f"findings: expected at least {expected['findings_count_min']}, got {actual_n}")

# 3. findings (list of partial-finding specs): for each expected, require at
#    least one actual finding matching all specified keys.
if "findings" in expected:
    for i, exp_f in enumerate(expected["findings"]):
        matched = False
        for act_f in actual.get("findings", []):
            ok = True
            for k, v in exp_f.items():
                if k == "sources":
                    if sorted(act_f.get("sources", [])) != sorted(v):
                        ok = False; break
                elif k == "source_finding_ids":
                    if sorted(act_f.get("source_finding_ids", [])) != sorted(v):
                        ok = False; break
                else:
                    if act_f.get(k) != v:
                        ok = False; break
            if ok:
                matched = True
                break
        if not matched:
            errors.append(f"findings[{i}]: no actual finding matched expected spec {exp_f!r}")

# 4. findings_by_file: map of file -> partial-finding spec.
if "findings_by_file" in expected:
    by_file = {f["file"]: f for f in actual.get("findings", [])}
    for fname, exp_f in expected["findings_by_file"].items():
        if fname not in by_file:
            errors.append(f"findings_by_file: file {fname!r} not present in actual findings")
            continue
        act_f = by_file[fname]
        for k, v in exp_f.items():
            if k == "recommended_fix_contains":
                if v not in (act_f.get("recommended_fix") or ""):
                    errors.append(f"findings_by_file[{fname}].recommended_fix: expected substring {v!r}, got {act_f.get('recommended_fix')!r}")
            else:
                if act_f.get(k) != v:
                    errors.append(f"findings_by_file[{fname}].{k}: expected {v!r}, got {act_f.get(k)!r}")

if errors:
    print(f"FAIL [{case_name}]:", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    sys.exit(1)
sys.exit(0)
PY
}

for fixture_dir in "$fixtures_root"/*/; do
  case_name=$(basename "$fixture_dir")
  total_cases=$((total_cases + 1))

  # Strip trailing slash so concatenated paths don't have "//" — Python's Path
  # normalizes that away in its error messages, which makes a literal grep fail.
  fixture_dir=${fixture_dir%/}
  safe_fail="$fixture_dir/safe-fail.md"
  mock_stub="$fixture_dir/mock-stub.md"
  expected="$fixture_dir/expected.json"
  known_clean="$fixture_dir/known-clean.txt"

  if [ ! -f "$safe_fail" ] || [ ! -f "$mock_stub" ] || [ ! -f "$expected" ]; then
    echo "FAIL [$case_name]: missing safe-fail.md, mock-stub.md, or expected.json" >&2
    failed_cases=$((failed_cases + 1))
    continue
  fi

  tmp_out=$(mktemp -d)
  # shellcheck disable=SC2064
  trap "rm -rf '$tmp_out'" EXIT

  # Malformed case: assert exit != 0 and stderr names the file + a line number.
  if [ "$case_name" = "case-06-malformed" ]; then
    set +e
    stderr_capture=$(python3 "$aggregator" \
      --safe-fail "$safe_fail" \
      --mock-stub "$mock_stub" \
      --out-dir "$tmp_out" \
      --scope test --date 2026-05-18 2>&1 >/dev/null)
    rc=$?
    set -e

    if [ "$rc" -eq 0 ]; then
      echo "FAIL [$case_name]: aggregator exited 0 on malformed input; expected non-zero" >&2
      failed_cases=$((failed_cases + 1))
      rm -rf "$tmp_out"
      trap - EXIT
      continue
    fi
    if ! printf '%s' "$stderr_capture" | grep -qF "$safe_fail"; then
      echo "FAIL [$case_name]: stderr does not name the safe-fail.md path" >&2
      echo "       stderr was:" >&2
      printf '%s\n' "$stderr_capture" | sed 's/^/         /' >&2
      failed_cases=$((failed_cases + 1))
      rm -rf "$tmp_out"
      trap - EXIT
      continue
    fi
    # Require "<path>:<digits>" pattern in the stderr (block start line).
    if ! printf '%s' "$stderr_capture" | grep -qE "$(printf '%s' "$safe_fail" | sed 's|[/.]|\\&|g'):[0-9]+"; then
      echo "FAIL [$case_name]: stderr does not contain '<safe-fail-path>:<line>' pattern" >&2
      echo "       stderr was:" >&2
      printf '%s\n' "$stderr_capture" | sed 's/^/         /' >&2
      failed_cases=$((failed_cases + 1))
      rm -rf "$tmp_out"
      trap - EXIT
      continue
    fi
    echo "OK   [$case_name]: aggregator exited non-zero with file:line in stderr"
    rm -rf "$tmp_out"
    trap - EXIT
    continue
  fi

  # Well-formed cases: run aggregator, compare AGGREGATE.json against expected subset.
  args=(
    --safe-fail "$safe_fail"
    --mock-stub "$mock_stub"
    --out-dir "$tmp_out"
    --scope "$case_name"
    --date 2026-05-18
  )
  if [ -f "$known_clean" ]; then
    args+=( --known-clean-surfaces "$known_clean" )
  fi

  if ! python3 "$aggregator" "${args[@]}" >/dev/null 2>"$tmp_out/stderr"; then
    echo "FAIL [$case_name]: aggregator exited non-zero on well-formed input" >&2
    sed 's/^/         /' "$tmp_out/stderr" >&2 || true
    failed_cases=$((failed_cases + 1))
    rm -rf "$tmp_out"
    trap - EXIT
    continue
  fi

  if ! assert_subset "$expected" "$tmp_out/AGGREGATE.json" "$case_name"; then
    failed_cases=$((failed_cases + 1))
    rm -rf "$tmp_out"
    trap - EXIT
    continue
  fi

  echo "OK   [$case_name]: AGGREGATE.json matches expected subset"
  rm -rf "$tmp_out"
  trap - EXIT
done

echo
echo "Summary: $total_cases cases, $failed_cases failures"

if [ "$failed_cases" = 0 ]; then
  exit 0
else
  exit 1
fi
