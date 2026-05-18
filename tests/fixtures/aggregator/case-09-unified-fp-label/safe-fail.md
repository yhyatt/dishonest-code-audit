### Finding ID: SF-001
Severity: FALSE-POSITIVE / INTENTIONAL
File: src/Toast.tsx
Line: 22
User-visible lie: createContext default handlers are no-ops; injected by provider
Evidence: |
  const ToastCtx = createContext({ show: () => {}, dismiss: () => {} });
Recommended fix: none — intentional pattern
Fix size: small
Confidence: high

