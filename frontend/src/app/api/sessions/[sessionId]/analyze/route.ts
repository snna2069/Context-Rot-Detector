import { NextResponse } from "next/server";

import { analyzeSession } from "@/lib/api/analysis";
import { ApiError } from "@/lib/api/client";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ sessionId: string }> },
) {
  const { sessionId } = await params;
  try {
    return NextResponse.json(await analyzeSession(sessionId), { status: 201 });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { error: "backend_request_failed", detail: error.message },
        { status: error.status || 502 },
      );
    }
    return NextResponse.json(
      { error: "analysis_proxy_failed" },
      { status: 502 },
    );
  }
}
