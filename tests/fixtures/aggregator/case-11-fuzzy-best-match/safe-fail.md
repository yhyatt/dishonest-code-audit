### Finding ID: SF-001
Severity: HIGH
File: src/route.ts
Line: 80
User-visible lie: route handler returns hardcoded sample data instead of querying the database
Evidence: |
  return NextResponse.json({ items: [/* sample */] });
Recommended fix: query the database
Fix size: medium
Confidence: high

