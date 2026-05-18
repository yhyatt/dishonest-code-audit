# Security policy

Found a security-sensitive issue, a prompt-injection bypass that defeats the guard in the audit flow, or a way the skill could be made to exfiltrate information from a victim's repo? Do not open a public issue.

Email: hyatt.yonatan@gmail.com

Include:

- A description of the issue.
- A minimal repro. A synthetic repo, a redacted snippet, or a transcript of the audit is fine.
- Whether you have coordinated with anyone else (e.g. Anthropic).

Expect a first response within 5 business days. Once a fix is in place, we will coordinate a public advisory (or a CHANGELOG note for non-critical issues) and credit you unless you prefer otherwise.

## Threat model

The plugin only ships markdown skills, bash helpers, and synthetic fixtures, so the threat model is mostly:

1. A malicious repository steers an audit via prompt injection (instructions hidden in source comments, i18n strings, lockfile annotations, etc.) to make the audit under-report.
2. A malicious profile contribution exfiltrates data through its grep commands or its `expected.json` content.
3. The harness's shell helpers misbehave on a hostile fixture name.

Reports in those categories are especially welcome.

## Out of scope

- Issues in `pr-review-toolkit` or `silent-failure-hunter`. Report those upstream.
- Issues in Claude Code itself. Report those to Anthropic.
- "The audit missed my stub": that is a bug report, not a security report. File a regular issue with the [bug template](.github/ISSUE_TEMPLATE/bug.md).
