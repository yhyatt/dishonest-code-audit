### Finding ID: SF-001
Severity: HIGH
File: src/save.ts
Line: 42
User-visible lie: toast claims saved but server returned 500
Status: bubbled through fetch.catch with empty handler
Evidence: |
  catch (e) { toast.success("saved"); }
Recommended fix: surface the server error
Fix size: small
Confidence: high

