### Finding ID: MS-001
Severity: HIGH
File: src/save.ts
Line: 42
User-visible lie: error swallowed and success toast shown
Evidence: |
  catch (e) { toast.success("saved"); }
Recommended fix: surface the server error
Fix size: small
Confidence: high

