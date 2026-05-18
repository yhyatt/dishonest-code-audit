### Finding ID: MS-001
Severity: MEDIUM
File: src/handlers.ts
Line: 200
User-visible lie: delete button onClick handler is empty arrow function
Evidence: |
  <button onClick={() => {}}>Delete</button>
Recommended fix: wire the handler to the delete endpoint
Fix size: medium
Confidence: medium

