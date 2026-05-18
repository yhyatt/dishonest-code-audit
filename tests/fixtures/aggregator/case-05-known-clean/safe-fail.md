### Finding ID: SF-001
Severity: MEDIUM
File: src/components/DemoSandbox.tsx
Line: 30
User-visible lie: button onClick is empty arrow function
Evidence: |
  <button onClick={() => {}}>Click</button>
Recommended fix: wire the handler
Fix size: small
Confidence: medium

