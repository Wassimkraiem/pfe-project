import { NextRequest, NextResponse } from "next/server";

const TRANSCRIBE_API_URL =
  process.env.TRANSCRIBE_API_URL ??
  process.env.CHAT_API_URL?.replace(/\/chat\/?$/, "/transcribe") ??
  "http://localhost:8003/api/v1/transcribe";

const TRANSCRIBE_API_KEY = process.env.CHAT_API_KEY ?? "change-me";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const incoming = await request.formData();
    const audio = incoming.get("audio");
    if (!(audio instanceof File)) {
      return NextResponse.json(
        { error: "Missing audio file" },
        { status: 400 },
      );
    }

    const formData = new FormData();
    formData.append("file", audio, audio.name || "recording.webm");

    const response = await fetch(TRANSCRIBE_API_URL, {
      method: "POST",
      headers: {
        "x-api-key": TRANSCRIBE_API_KEY,
      },
      body: formData,
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
      { error: "Failed to transcribe audio" },
      { status: 502 },
    );
  }
}
