### Finding ID: MS-001
Severity: HIGH
File: src/components/save.tsx
Line: 42
User-visible lie: button promises save, never calls server
Evidence: |
  <Button onClick={() => {}}>save</Button>
Recommended fix: wire the handler
Fix size: small
Confidence: high

