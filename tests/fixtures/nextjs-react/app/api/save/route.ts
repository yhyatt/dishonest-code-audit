// Synthetic fixture — intentionally returns canned mock-data instead of querying a real source.

import { NextResponse } from "next/server";

export async function POST() {
  // HIGH: route handler returns hardcoded mock-data — no DB write, no validation.
  return NextResponse.json({
    ok: true,
    item: { id: "mock-id", value: "mock-data placeholder" },
  });
}
