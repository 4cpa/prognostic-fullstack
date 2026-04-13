import { NextRequest, NextResponse } from "next/server";

function getBackendUrl(): string {
  return (
    process.env.INTERNAL_API_BASE_URL ||
    process.env.NEXT_PUBLIC_INTERNAL_API_BASE_URL ||
    process.env.API_BASE_URL ||
    "http://backend:8000"
  ).replace(/\/+$/, "");
}

export async function POST(req: NextRequest) {
  const anthropicKey = req.headers.get("x-anthropic-key") ?? "";
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (anthropicKey) {
    headers["X-Anthropic-Key"] = anthropicKey;
  }

  try {
    const res = await fetch(`${getBackendUrl()}/questions`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const data: unknown = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json(
      { error: `Backend nicht erreichbar: ${String(err)}` },
      { status: 502 },
    );
  }
}
