import { NextRequest, NextResponse } from "next/server";

const RAG_API_BASE_URL =
  process.env.RAG_API_URL ??
  process.env.CHAT_API_URL?.replace(/\/chat\/?$/, "/rag") ??
  "http://localhost:8003/api/v1/rag";
const CHAT_API_KEY = process.env.CHAT_API_KEY ?? "change-me";

export const runtime = "nodejs";

function vectorUrl(pointId: string): string {
  return `${RAG_API_BASE_URL.replace(/\/$/, "")}/vectors/${encodeURIComponent(pointId)}`;
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ pointId: string }> },
) {
  try {
    const { pointId } = await params;
    const response = await fetch(vectorUrl(pointId), {
      method: "GET",
      headers: { "x-api-key": CHAT_API_KEY },
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
    return NextResponse.json({ error: "Failed to reach FAQ vector service" }, { status: 502 });
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ pointId: string }> },
) {
  try {
    const { pointId } = await params;
    const body = await request.json();
    const response = await fetch(vectorUrl(pointId), {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": CHAT_API_KEY,
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
    return NextResponse.json({ error: "Failed to reach FAQ vector service" }, { status: 502 });
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ pointId: string }> },
) {
  try {
    const { pointId } = await params;
    const response = await fetch(vectorUrl(pointId), {
      method: "DELETE",
      headers: { "x-api-key": CHAT_API_KEY },
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
    return NextResponse.json({ error: "Failed to reach FAQ vector service" }, { status: 502 });
  }
}
