#!/usr/bin/env python3
"""Deterministic aggregator for dishonest-code-audit source reports.

Parses structured `### Finding ID:` blocks from SAFE-FAIL-AUDIT.md and
MOCK-STUB-AUDIT.md, deduplicates them per the spec in
skills/dishonest-code-audit/SKILL.md, and emits:

  1. A JSON sidecar (`AGGREGATE.json`) — single source of truth for findings,
     dedup pairings, severity merges, counts.
  2. A Markdown skeleton (`DISHONEST-CODE-AUDIT.md`) with mechanical sections
     filled and `<!-- LLM_FILL: ... -->` placeholders for the narrative parts
     (headline, dominant patterns, cross-audit gaps).

Fails loud, never silent. Any unparseable block exits non-zero with the file
and line that broke. The wet-run motivation for this script is "the orchestrator
LLM miscounts"; a silently-broken parser produces the same failure shape.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


SEVERITY_RANK = {
    "HIGH": 4,
    "MEDIUM": 3,
    "LOW": 2,
    "FALSE-POSITIVE": 1,
    "FALSE-POSITIVE / INTENTIONAL": 1,
    "INTENTIONAL": 1,
}

# Required fields per the schema in skills/stub-audit/SKILL.md
REQUIRED_FIELDS = (
    "Severity",
    "File",
    "Line",
    "User-visible lie",
    "Evidence",
    "Recommended fix",
    "Fix size",
    "Confidence",
)

FIELD_RE = re.compile(r"^([A-Z][A-Za-z\- ]+?):\s*(.*)$")
HEADER_RE = re.compile(r"^### Finding ID:\s*(\S+)\s*$")


@dataclass
class Finding:
    source: str  # 'safe-fail' | 'mock-stub'
    source_path: str
    finding_id: str
    severity: str
    file: str
    line_raw: str
    line_primary: Optional[int]
    user_visible_lie: str
    evidence: str
    recommended_fix: str
    fix_size: str
    confidence: str
    extra_fields: dict = field(default_factory=dict)
    block_start_line: int = 0


def normalize_severity(value: str) -> str:
    """Normalize a severity string to the canonical vocabulary."""
    v = value.strip().upper()
    # Accept some legacy aliases that drift in practice.
    if v in {"FP", "FALSE POSITIVE"}:
        v = "FALSE-POSITIVE"
    if v in {"NONE-INTENTIONAL", "NONE/INTENTIONAL"}:
        v = "INTENTIONAL"
    if v not in SEVERITY_RANK:
        raise ValueError(f"unknown severity: {value!r}")
    return v


def normalize_path(p: str, repo_root: Optional[str]) -> str:
    """Strip repo-root prefix and leading ./, collapse duplicate slashes."""
    p = p.strip()
    if repo_root:
        rr = repo_root.rstrip("/") + "/"
        if p.startswith(rr):
            p = p[len(rr):]
    while p.startswith("./"):
        p = p[2:]
    p = re.sub(r"/+", "/", p)
    return p


def extract_line_primary(line_value: str) -> Optional[int]:
    """Pull the first integer out of a Line: value.

    Accepts: '123', '123-456', '40, 47, 57', 'unknown', 'N/A'.
    Returns None for unknown / N/A / no integer found.
    """
    v = line_value.strip()
    if v.lower() in {"unknown", "n/a", "na", ""}:
        return None
    m = re.search(r"\d+", v)
    return int(m.group(0)) if m else None


def tokenize(text: str) -> set[str]:
    """Token set for Jaccard similarity. Lowercase, alphanumeric, length >= 3."""
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) >= 3}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def parse_report(path: Path, source_label: str, repo_root: Optional[str]) -> list[Finding]:
    """Parse a single source report into a list of Findings.

    Fails loud on any malformed block (missing required field, bad severity).
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    findings: list[Finding] = []

    i = 0
    n = len(lines)
    while i < n:
        m = HEADER_RE.match(lines[i])
        if not m:
            i += 1
            continue

        block_start = i + 1  # 1-indexed for error messages
        finding_id = m.group(1)
        i += 1

        fields: dict[str, str] = {}
        evidence_lines: list[str] = []
        cur_field: Optional[str] = None

        while i < n:
            line = lines[i]
            if HEADER_RE.match(line):
                break
            # Top-level field line: "Key: value"
            fm = FIELD_RE.match(line)
            if fm and not line.startswith(" ") and not line.startswith("\t"):
                key = fm.group(1).strip()
                value = fm.group(2)
                # Pipe-block evidence: "Evidence: |"
                if key == "Evidence" and value.strip() == "|":
                    cur_field = "Evidence"
                    fields["Evidence"] = ""
                    i += 1
                    continue
                fields[key] = value.rstrip()
                cur_field = key
                i += 1
                continue

            # Continuation line. If we're in an Evidence pipe-block, accumulate.
            if cur_field == "Evidence" and (line.startswith("  ") or line == ""):
                evidence_lines.append(line[2:] if line.startswith("  ") else "")
                i += 1
                continue

            # Other continuation: append to last field (handles wrapped User-visible lie etc.)
            if cur_field and line.strip():
                fields[cur_field] = (fields.get(cur_field, "") + " " + line.strip()).strip()
                i += 1
                continue

            # Blank line outside Evidence ends the block.
            if not line.strip():
                i += 1
                break

            i += 1

        if evidence_lines:
            fields["Evidence"] = "\n".join(evidence_lines).rstrip()

        # Validate required fields are present.
        missing = [k for k in REQUIRED_FIELDS if k not in fields]
        if missing:
            raise ValueError(
                f"{path}:{block_start}: finding {finding_id} missing required fields: {missing}"
            )

        try:
            severity = normalize_severity(fields["Severity"])
        except ValueError as e:
            raise ValueError(f"{path}:{block_start}: finding {finding_id}: {e}")

        line_raw = fields["Line"].strip()
        line_primary = extract_line_primary(line_raw)

        # Pull out fields we recognize; route the rest into extra_fields.
        recognized = {
            "Severity", "File", "Line", "User-visible lie", "Evidence",
            "Recommended fix", "Fix size", "Confidence",
        }
        extras = {k: v for k, v in fields.items() if k not in recognized}

        findings.append(Finding(
            source=source_label,
            source_path=str(path),
            finding_id=finding_id,
            severity=severity,
            file=normalize_path(fields["File"], repo_root),
            line_raw=line_raw,
            line_primary=line_primary,
            user_visible_lie=fields["User-visible lie"].strip(),
            evidence=fields["Evidence"].strip(),
            recommended_fix=fields["Recommended fix"].strip(),
            fix_size=fields["Fix size"].strip(),
            confidence=fields["Confidence"].strip(),
            extra_fields=extras,
            block_start_line=block_start,
        ))

    return findings


@dataclass
class MergedFinding:
    severity: str  # max-merged
    file: str
    line_raw: str
    line_primary: Optional[int]
    user_visible_lie: str
    evidence: str
    recommended_fix: str
    fix_size: str
    confidence: str
    sources: list[str]  # ['safe-fail', 'mock-stub'] or one
    source_finding_ids: list[str]
    severity_disagreement: Optional[str]  # textual record when sides disagreed
    known_clean_match: Optional[str] = None  # caller-supplied reason if matched

    def source_label(self) -> str:
        if len(self.sources) == 1:
            return self.sources[0]
        return "both"


def merge_pair(a: Finding, b: Finding) -> MergedFinding:
    """Merge two findings deduped to the same site."""
    if SEVERITY_RANK[a.severity] >= SEVERITY_RANK[b.severity]:
        primary, secondary = a, b
    else:
        primary, secondary = b, a

    if a.severity != b.severity:
        disagreement = f"{a.source}: {a.severity}, {b.source}: {b.severity}"
    else:
        disagreement = None

    return MergedFinding(
        severity=primary.severity,
        file=primary.file,
        line_raw=primary.line_raw if primary.line_primary is not None else (
            secondary.line_raw if secondary.line_primary is not None else primary.line_raw
        ),
        line_primary=primary.line_primary if primary.line_primary is not None else secondary.line_primary,
        user_visible_lie=primary.user_visible_lie,
        evidence=primary.evidence,
        recommended_fix=primary.recommended_fix,
        fix_size=primary.fix_size,
        confidence=primary.confidence,
        sources=sorted({a.source, b.source}),
        source_finding_ids=sorted({a.finding_id, b.finding_id}),
        severity_disagreement=disagreement,
    )


def deduplicate(findings: list[Finding], jaccard_threshold: float = 0.6) -> list[MergedFinding]:
    """Apply the dedup rules from SKILL.md.

    Primary key: (normalize_path(File), line_primary). When line is unknown on
    either side, fall back to token-overlap on user_visible_lie >= threshold,
    matched within the same File only.
    """
    safe_fail = [f for f in findings if f.source == "safe-fail"]
    mock_stub = [f for f in findings if f.source == "mock-stub"]

    # Index mock-stub by primary key for O(1) lookup.
    ms_by_key: dict[tuple[str, int], Finding] = {}
    ms_by_file: dict[str, list[Finding]] = {}
    for f in mock_stub:
        if f.line_primary is not None:
            ms_by_key[(f.file, f.line_primary)] = f
        ms_by_file.setdefault(f.file, []).append(f)

    merged: list[MergedFinding] = []
    consumed_ms: set[str] = set()  # finding_ids of consumed mock-stub findings

    for sf in safe_fail:
        partner: Optional[Finding] = None

        # Primary: exact (file, line) match.
        if sf.line_primary is not None:
            key = (sf.file, sf.line_primary)
            cand = ms_by_key.get(key)
            if cand and cand.finding_id not in consumed_ms:
                partner = cand

        # Fallback: same file, fuzzy lie match. Only when at least one side has
        # an unknown line (per spec); otherwise primary-key mismatch means
        # different sites in the same file.
        if partner is None:
            sf_tokens = tokenize(sf.user_visible_lie)
            for cand in ms_by_file.get(sf.file, []):
                if cand.finding_id in consumed_ms:
                    continue
                if sf.line_primary is not None and cand.line_primary is not None:
                    # Both have lines and they didn't match in the primary pass.
                    continue
                score = jaccard(sf_tokens, tokenize(cand.user_visible_lie))
                if score >= jaccard_threshold:
                    partner = cand
                    break

        if partner is not None:
            merged.append(merge_pair(sf, partner))
            consumed_ms.add(partner.finding_id)
        else:
            merged.append(_as_merged(sf))

    # Unconsumed mock-stub findings ride alone.
    for f in mock_stub:
        if f.finding_id not in consumed_ms:
            merged.append(_as_merged(f))

    return merged


def _as_merged(f: Finding) -> MergedFinding:
    return MergedFinding(
        severity=f.severity,
        file=f.file,
        line_raw=f.line_raw,
        line_primary=f.line_primary,
        user_visible_lie=f.user_visible_lie,
        evidence=f.evidence,
        recommended_fix=f.recommended_fix,
        fix_size=f.fix_size,
        confidence=f.confidence,
        sources=[f.source],
        source_finding_ids=[f.finding_id],
        severity_disagreement=None,
    )


def parse_known_clean(text: Optional[str]) -> list[tuple[str, str, str]]:
    """Parse known_clean_surfaces input.

    Accepts the YAML-ish form documented in SKILL.md, one entry per line:
        path/to/file.tsx:symbol — reason
    Returns list of (file, symbol, reason) tuples. Symbol is empty when omitted.
    Lines starting with `#`, blank lines, and a leading `known_clean_surfaces:`
    header are ignored.
    """
    if not text:
        return []
    out: list[tuple[str, str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("known_clean_surfaces"):
            continue
        if line.startswith("- "):
            line = line[2:]
        # Split on em dash or " — " or " - "
        m = re.match(r"^(.+?)\s+[—-]\s+(.+)$", line)
        if not m:
            continue
        target, reason = m.group(1).strip(), m.group(2).strip()
        if ":" in target:
            f, sym = target.split(":", 1)
            out.append((f.strip(), sym.strip(), reason))
        else:
            out.append((target, "", reason))
    return out


def apply_known_clean(merged: list[MergedFinding], clean: list[tuple[str, str, str]]) -> None:
    """Reclassify any merged finding whose file (and symbol-text) matches a
    known-clean entry as FALSE-POSITIVE / INTENTIONAL, recording the reason.
    """
    for mf in merged:
        for cf, sym, reason in clean:
            if mf.file == cf or mf.file.endswith("/" + cf):
                if not sym or sym.lower() in mf.user_visible_lie.lower() or sym.lower() in mf.evidence.lower():
                    mf.severity = "INTENTIONAL"
                    mf.known_clean_match = reason
                    mf.recommended_fix = f"none — marked clean by caller: {reason}"
                    break


def render_finding_block(mf: MergedFinding, new_id: str) -> str:
    """Render a merged finding as a Markdown block matching the source schema."""
    src_ids = ", ".join(mf.source_finding_ids)
    sev_disagreement = mf.severity_disagreement or "none"

    evidence = mf.evidence
    if evidence.count("\n") > 0 or len(evidence) > 80:
        # Multi-line pipe form
        ev_lines = evidence.split("\n")
        evidence_block = "Evidence: |\n" + "\n".join("  " + l for l in ev_lines)
    else:
        evidence_block = f"Evidence: {evidence}"

    return (
        f"### Finding ID: {new_id}\n"
        f"Source: {mf.source_label()}\n"
        f"Severity: {mf.severity}\n"
        f"File: {mf.file}\n"
        f"Line: {mf.line_raw}\n"
        f"User-visible lie: {mf.user_visible_lie}\n"
        f"{evidence_block}\n"
        f"Recommended fix: {mf.recommended_fix}\n"
        f"Fix size: {mf.fix_size}\n"
        f"Confidence: {mf.confidence}\n"
        f"Source-finding IDs: {src_ids}\n"
        f"Severity disagreement: {sev_disagreement}\n"
    )


def render_markdown(
    merged: list[MergedFinding],
    counts: dict,
    scope: str,
    date: str,
    safe_fail_path: str,
    mock_stub_path: str,
    known_clean: list[tuple[str, str, str]],
) -> str:
    by_sev: dict[str, list[MergedFinding]] = {"HIGH": [], "MEDIUM": [], "LOW": [], "INTENTIONAL": []}
    for mf in merged:
        if mf.severity == "FALSE-POSITIVE" or mf.severity == "INTENTIONAL":
            by_sev["INTENTIONAL"].append(mf)
        else:
            by_sev[mf.severity].append(mf)

    high_idx = 0
    medium_idx = 0
    high_blocks: list[str] = []
    medium_blocks: list[str] = []
    for mf in by_sev["HIGH"]:
        high_idx += 1
        high_blocks.append(render_finding_block(mf, f"HIGH-{high_idx:03d}"))
    for mf in by_sev["MEDIUM"]:
        medium_idx += 1
        medium_blocks.append(render_finding_block(mf, f"MED-{medium_idx:03d}"))

    low_bullets = [
        f"- `{mf.file}:{mf.line_raw}` ({', '.join(mf.source_finding_ids)}) — {mf.user_visible_lie}"
        for mf in by_sev["LOW"]
    ]
    fp_bullets = [
        f"- `{mf.file}:{mf.line_raw}` ({', '.join(mf.source_finding_ids)}) — {mf.user_visible_lie}"
        + (f" *[clean: {mf.known_clean_match}]*" if mf.known_clean_match else "")
        for mf in by_sev["INTENTIONAL"]
    ]

    clean_section_lines = [
        f"- `{cf}` ({sym or '—'}): {reason}" for cf, sym, reason in known_clean
    ]

    parts: list[str] = []
    parts.append(f"# Dishonest Code Audit: {scope}\n")
    parts.append(f"Date: {date}")
    parts.append(f"Scope: {scope}")
    parts.append("")
    parts.append("<!-- LLM_FILL: headline — one sentence describing what's NOT broken, mirroring the dominant patterns below. -->\n")
    parts.append("## Combined verdict\n")
    parts.append(f"- HIGH findings: {counts['safe_high']} safe-fail + {counts['mock_high']} mock/stub - {counts['high_overlap']} dedup overlaps = **{counts['high_total']}**")
    parts.append(f"- MEDIUM: {counts['safe_medium']} safe-fail + {counts['mock_medium']} mock/stub - {counts['medium_overlap']} dedup overlaps = **{counts['medium_total']}**")
    parts.append(f"- LOW: {counts['safe_low']} safe-fail + {counts['mock_low']} mock/stub - {counts['low_overlap']} dedup overlaps = **{counts['low_total']}**")
    parts.append(f"- FALSE-POSITIVE / INTENTIONAL: {counts['intentional_total']}")
    parts.append("")
    parts.append("<!-- LLM_FILL: dominant_patterns — group HIGH findings into 1-3 dominant patterns. -->\n")
    parts.append("## HIGH — block before ship\n")
    parts.extend(high_blocks if high_blocks else ["_None._"])
    parts.append("")
    parts.append("## MEDIUM — fix this sprint\n")
    parts.extend(medium_blocks if medium_blocks else ["_None._"])
    parts.append("")
    parts.append("## LOW — defer\n")
    parts.extend(low_bullets if low_bullets else ["_None._"])
    parts.append("")
    parts.append("## False positives / intentional patterns\n")
    parts.extend(fp_bullets if fp_bullets else ["_None._"])
    if clean_section_lines:
        parts.append("")
        parts.append("### Known-clean surfaces (caller-supplied; verified)\n")
        parts.extend(clean_section_lines)
    parts.append("")
    parts.append("## Cross-audit gaps (tuning signal)\n")
    parts.append("<!-- LLM_FILL: cross_audit_gaps — review the `single_source_findings` array in AGGREGATE.json. For each, judge whether the OTHER specialist could have caught it from their own framing. Format: `<HIGH-ID>: <which specialist caught it> — <which specialist could have caught it independently and didn't> — <one-line tuning suggestion>`. Write `None — every finding sits on a single specialist's domain.` if no feasible cross-coverage. -->\n")
    parts.append("## Coverage notes\n")
    parts.append("<!-- LLM_FILL: coverage_notes — profiles loaded, globs scanned, globs excluded, tools that ran vs unavailable. Pull from the source reports' Coverage notes sections. -->\n")
    parts.append("## Source reports")
    parts.append(f"- Safe-fail: `{safe_fail_path}`")
    parts.append(f"- Mock/stub: `{mock_stub_path}`")
    parts.append("- Machine-readable: `AGGREGATE.json` (this directory)\n")

    return "\n".join(parts)


def build_counts(safe: list[Finding], mock: list[Finding], merged: list[MergedFinding]) -> dict:
    def count_sev(findings, sev): return sum(1 for f in findings if f.severity == sev)
    def count_merged_sev(sev): return sum(1 for m in merged if m.severity == sev)
    def overlap_sev(sev):
        return sum(1 for m in merged if len(m.sources) == 2 and m.severity == sev)
    return {
        "safe_high": count_sev(safe, "HIGH"),
        "safe_medium": count_sev(safe, "MEDIUM"),
        "safe_low": count_sev(safe, "LOW"),
        "mock_high": count_sev(mock, "HIGH"),
        "mock_medium": count_sev(mock, "MEDIUM"),
        "mock_low": count_sev(mock, "LOW"),
        "high_overlap": overlap_sev("HIGH"),
        "medium_overlap": overlap_sev("MEDIUM"),
        "low_overlap": overlap_sev("LOW"),
        "high_total": count_merged_sev("HIGH"),
        "medium_total": count_merged_sev("MEDIUM"),
        "low_total": count_merged_sev("LOW"),
        "intentional_total": sum(1 for m in merged if m.severity in {"FALSE-POSITIVE", "INTENTIONAL"}),
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--safe-fail", required=True, type=Path, help="Path to SAFE-FAIL-AUDIT.md")
    ap.add_argument("--mock-stub", required=True, type=Path, help="Path to MOCK-STUB-AUDIT.md")
    ap.add_argument("--out-dir", required=True, type=Path, help="Output directory for AGGREGATE.json and DISHONEST-CODE-AUDIT.md")
    ap.add_argument("--repo-root", default=None, help="Repo root prefix to strip from File: paths")
    ap.add_argument("--scope", default="(scope not provided)", help="Scope description for the report header")
    ap.add_argument("--date", default=None, help="ISO date for the report header; defaults to today")
    ap.add_argument("--known-clean-surfaces", default=None, type=Path, help="Path to a text file listing known-clean surfaces (one per line: `path:symbol — reason`)")
    ap.add_argument("--jaccard-threshold", default=0.6, type=float, help="Fuzzy-match threshold for User-visible lie when Line is unknown")
    args = ap.parse_args(argv)

    if not args.safe_fail.exists():
        print(f"ERROR: --safe-fail path does not exist: {args.safe_fail}", file=sys.stderr)
        return 2
    if not args.mock_stub.exists():
        print(f"ERROR: --mock-stub path does not exist: {args.mock_stub}", file=sys.stderr)
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)

    safe = parse_report(args.safe_fail, "safe-fail", args.repo_root)
    mock = parse_report(args.mock_stub, "mock-stub", args.repo_root)

    merged = deduplicate(safe + mock, jaccard_threshold=args.jaccard_threshold)

    known_clean = []
    if args.known_clean_surfaces and args.known_clean_surfaces.exists():
        known_clean = parse_known_clean(args.known_clean_surfaces.read_text(encoding="utf-8"))
        apply_known_clean(merged, known_clean)

    counts = build_counts(safe, mock, merged)

    from datetime import date as _date
    iso_date = args.date or _date.today().isoformat()

    single_source = [
        {
            "severity": m.severity,
            "file": m.file,
            "line": m.line_raw,
            "source": m.sources[0],
            "source_finding_id": m.source_finding_ids[0],
            "user_visible_lie": m.user_visible_lie,
        }
        for m in merged
        if len(m.sources) == 1 and m.severity in {"HIGH", "MEDIUM"}
    ]

    aggregate_json = {
        "scope": args.scope,
        "date": iso_date,
        "counts": counts,
        "findings": [asdict(m) for m in merged],
        "single_source_findings": single_source,
        "known_clean_surfaces": [
            {"file": cf, "symbol": sym, "reason": reason} for cf, sym, reason in known_clean
        ],
        "source_reports": {
            "safe_fail": str(args.safe_fail),
            "mock_stub": str(args.mock_stub),
        },
    }

    (args.out_dir / "AGGREGATE.json").write_text(
        json.dumps(aggregate_json, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    md = render_markdown(
        merged=merged,
        counts=counts,
        scope=args.scope,
        date=iso_date,
        safe_fail_path=str(args.safe_fail),
        mock_stub_path=str(args.mock_stub),
        known_clean=known_clean,
    )
    (args.out_dir / "DISHONEST-CODE-AUDIT.md").write_text(md, encoding="utf-8")

    print(
        f"OK   aggregated: HIGH={counts['high_total']} MEDIUM={counts['medium_total']} "
        f"LOW={counts['low_total']} INTENTIONAL={counts['intentional_total']} "
        f"(overlaps: H={counts['high_overlap']} M={counts['medium_overlap']} L={counts['low_overlap']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
