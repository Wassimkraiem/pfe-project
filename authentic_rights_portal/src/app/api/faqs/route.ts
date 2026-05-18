import { NextRequest, NextResponse } from "next/server";

const RAG_API_BASE_URL =
  process.env.RAG_API_URL ??
  process.env.CHAT_API_URL?.replace(/\/chat\/?$/, "/rag") ??
  "http://localhost:8003/api/v1/rag";
const CHAT_API_KEY = process.env.CHAT_API_KEY ?? "change-me";
const DEFAULT_FAQ_SOURCE = process.env.FAQ_VECTOR_SOURCE ?? "q&a";
const FAQ_SOURCE_ALIASES: Record<string, string> = {
  "q&a": "bviral_qas",
  qna: "bviral_qas",
  qa: "bviral_qas",
  qas: "bviral_qas",
  bviral_qas: "bviral_qas",
  faq: "faq",
};

export const runtime = "nodejs";

function normalizeFaqSource(source: string | null | undefined): string {
  const value = source?.trim();
  if (!value) {
    return FAQ_SOURCE_ALIASES["q&a"];
  }
  const alias = FAQ_SOURCE_ALIASES[value.toLowerCase()];
  return alias ?? value;
}

function buildUrl(request: NextRequest): string {
  const url = new URL(`${RAG_API_BASE_URL.replace(/\/$/, "")}/vectors`);
  const limit = request.nextUrl.searchParams.get("limit");
  const offset = request.nextUrl.searchParams.get("offset");
  const source = normalizeFaqSource(
    request.nextUrl.searchParams.get("source") ?? DEFAULT_FAQ_SOURCE,
  );
  if (limit) url.searchParams.set("limit", limit);
  if (offset) url.searchParams.set("offset", offset);
  if (source) url.searchParams.set("source", source);
  return url.toString();
}

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(buildUrl(request), {
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

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const payload = {
      ...body,
      source: normalizeFaqSource(
        typeof body.source === "string" ? body.source : DEFAULT_FAQ_SOURCE,
      ),
    };

    const response = await fetch(`${RAG_API_BASE_URL.replace(/\/$/, "")}/vectors`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": CHAT_API_KEY,
      },
      body: JSON.stringify(payload),
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
