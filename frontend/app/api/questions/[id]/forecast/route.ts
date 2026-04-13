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
  const url = new URL(req.url);
  const methodVersion = url.searchParams.get("method_version") ?? "v0.1.0";
  const language = url.searchParams.get("language") ?? "de";

  try {
    const res = await fetch(
      `${getBackendUrl()}/questions/${id}/forecast?method_version=${methodVersion}&language=${language}`,
      {
        method: "POST",
        headers: { Accept: "application/json" },
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
