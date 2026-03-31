import { NextRequest, NextResponse } from "next/server";

const CHAT_API_URL = process.env.CHAT_API_URL ?? "http://localhost:8003/api/v1/chat";
const CHAT_API_KEY = process.env.CHAT_API_KEY ?? "change-me";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const userId =
      typeof body.user_id === "string" && body.user_id.trim().length > 0
        ? body.user_id
        : "web-anonymous";

    const response = await fetch(CHAT_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": CHAT_API_KEY,
        "x-user-id": userId,
      },
      body: JSON.stringify(body),
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
