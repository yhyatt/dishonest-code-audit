### Finding ID: SF-001
Severity: HIGH
File: src/handlers.ts
Line: 10
User-visible lie: payment confirmation toast shown when stripe returned decline
Evidence: |
  try { stripe.charge(); } catch { toast("paid"); }
Recommended fix: surface decline reason to user
Fix size: small
Confidence: high

