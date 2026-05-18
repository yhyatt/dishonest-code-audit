### Finding ID: MS-001
Severity: MEDIUM
File: src/demo/Sandbox.tsx
Line: 12
User-visible lie: button labelled "save" with empty onClick in demo path
Evidence: |
  <Button onClick={() => {}}>save</Button>
Recommended fix: wire the handler or remove the button
Fix size: small
Confidence: high

