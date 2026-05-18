#!/usr/bin/env bash
# Extract ```bash fenced blocks from a markdown file and write them to stdout.
# Used by the CI shellcheck step.
#
# Usage: extract-bash.sh path/to/file.md

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <markdown-file>" >&2
  exit 2
fi

file="$1"

if [ ! -f "$file" ]; then
  echo "ERROR: $file not found" >&2
  exit 2
fi

awk '
  BEGIN { in_block = 0 }
  /^```bash[ \t]*$/ { in_block = 1; next }
  /^```[ \t]*$/ { if (in_block == 1) { in_block = 0; print "" } ; next }
  { if (in_block == 1) print }
' "$file"
