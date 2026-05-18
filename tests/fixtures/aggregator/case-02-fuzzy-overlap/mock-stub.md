### Finding ID: MS-001
Severity: MEDIUM
File: src/clipboard.ts
Line: unknown
User-visible lie: clipboard copied toast shown when writeText promise rejected silently
Evidence: |
  navigator.clipboard.writeText(x).catch(() => {}); toast("copied");
Recommended fix: await the promise and toast only on resolve
Fix size: small
Confidence: high

