import { NextRequest, NextResponse } from "next/server";

function getBackendUrl(): string {
  return (
    process.env.INTERNAL_API_BASE_URL ||
    process.env.NEXT_PUBLIC_INTERNAL_API_BASE_URL ||
    process.env.API_BASE_URL ||
    "http://backend:8000"
  ).replace(/\/+$/, "");
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const anthropicKey = req.headers.get("x-anthropic-key") ?? "";
  const methodVersion =
    new URL(req.url).searchParams.get("method_version") ?? "v0.1.0";

  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (anthropicKey) {
    headers["X-Anthropic-Key"] = anthropicKey;
  }

  try {
    const res = await fetch(
      `${getBackendUrl()}/questions/${id}/forecast?method_version=${methodVersion}`,
      {
        method: "POST",
        headers,
        cache: "no-store",
      },
    );
    const data: unknown = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json(
      { error: `Backend nicht erreichbar: ${String(err)}` },
      { status: 502 },
    );
  }
}
