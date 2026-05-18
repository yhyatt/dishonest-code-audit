### Finding ID: MS-001
Severity: MEDIUM
File: src/upload.ts
Line: 15
User-visible lie: upload toast says done when fetch returned 500
Evidence: |
  fetch(url).catch(() => {}); toast("done");
Recommended fix: check response.ok and surface failure
Fix size: small
Confidence: medium

