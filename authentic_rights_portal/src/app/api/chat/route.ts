import { NextRequest, NextResponse } from "next/server";

const CHAT_API_URL = process.env.CHAT_API_URL ?? "http://localhost:8003/api/v1/chat";
const CHAT_API_KEY = process.env.CHAT_API_KEY ?? "change-me";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const normalizedBody = { ...body };
    if (normalizedBody.mode === "chat") {
      normalizedBody.mode = "default";
    }
    const userId =
      typeof normalizedBody.user_id === "string" && normalizedBody.user_id.trim().length > 0
        ? normalizedBody.user_id
        : "web-anonymous";

    const response = await fetch(CHAT_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": CHAT_API_KEY,
        "x-user-id": userId,
      },
      body: JSON.stringify(normalizedBody),
      cache: "no-store",
    });

    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") ?? "application/json",
      },
    });
  } catch {
    return NextResponse.json(
      { error: "Failed to reach chat service" },
      { status: 502 }
    );
  }
}
