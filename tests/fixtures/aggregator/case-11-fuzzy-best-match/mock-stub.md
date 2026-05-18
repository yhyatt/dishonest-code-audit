### Finding ID: MS-001
Severity: MEDIUM
File: src/route.ts
Line: unknown
User-visible lie: route handler returns sample database items somewhere in the file
Evidence: |
  // somewhere in route.ts
Recommended fix: investigate
Fix size: small
Confidence: low

### Finding ID: MS-002
Severity: HIGH
File: src/route.ts
Line: unknown
User-visible lie: route handler returns hardcoded sample data instead of querying the database
Evidence: |
  return NextResponse.json({ items: [/* sample */] });
Recommended fix: query the database
Fix size: medium
Confidence: high

