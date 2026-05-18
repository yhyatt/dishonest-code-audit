### Finding ID: SF-001
Severity: HIGH
File: src/save.ts
Line: 42
User-visible lie: toast says saved when server returned 500
Evidence: |
  catch (e) { toast.success("saved"); }
Recommended fix: surface the server error
Fix size: small
Confidence: high

