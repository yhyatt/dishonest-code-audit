#!/usr/bin/env bash
# Validate skill SKILL.md frontmatter.
#
# Asserts:
#   - YAML frontmatter exists between `---` markers at the top of the file
#   - `name:` key is present and matches the parent directory name
#   - `description:` key is present and non-empty
#
# Usage: validate-frontmatter.sh [path-to-skills-root]
# Default skills root: ./skills

set -euo pipefail

skills_root="${1:-skills}"

if [ ! -d "$skills_root" ]; then
  echo "ERROR: skills directory not found at $skills_root" >&2
  exit 2
fi

overall_fail=0

while IFS= read -r -d '' skill_md; do
  skill_dir=$(dirname "$skill_md")
  expected_name=$(basename "$skill_dir")
  file_fail=0

  if ! head -1 "$skill_md" | grep -qx '\-\-\-'; then
    echo "FAIL [$skill_md]: missing opening --- frontmatter marker" >&2
    overall_fail=1
    continue
  fi

  marker_count=$(awk '/^---$/ { c++ } END { print c+0 }' "$skill_md")
  if [ "$marker_count" -lt 2 ]; then
    echo "FAIL [$skill_md]: missing closing --- frontmatter marker (found $marker_count of 2)" >&2
    overall_fail=1
    continue
  fi

  frontmatter=$(awk 'NR==1 && /^---$/ { in_fm=1; next } in_fm && /^---$/ { exit } in_fm { print }' "$skill_md")

  if [ -z "$frontmatter" ]; then
    echo "FAIL [$skill_md]: frontmatter is empty" >&2
    overall_fail=1
    continue
  fi

  name_value=$(printf '%s\n' "$frontmatter" | awk -F': *' '/^name:/ { print $2; exit }')
  desc_value=$(printf '%s\n' "$frontmatter" | awk -F': *' '/^description:/ { sub(/^description: */, ""); print; exit }')

  if [ -z "$name_value" ]; then
    echo "FAIL [$skill_md]: missing 'name:' key" >&2
    file_fail=1
  elif [ "$name_value" != "$expected_name" ]; then
    echo "FAIL [$skill_md]: name '$name_value' does not match directory '$expected_name'" >&2
    file_fail=1
  fi

  if [ -z "$desc_value" ]; then
    echo "FAIL [$skill_md]: missing or empty 'description:' key" >&2
    file_fail=1
  fi

  if [ "$file_fail" = 0 ]; then
    echo "OK   [$skill_md]: name=$name_value"
  else
    overall_fail=1
  fi
done < <(find "$skills_root" -mindepth 2 -maxdepth 2 -name SKILL.md -print0)

exit "$overall_fail"
