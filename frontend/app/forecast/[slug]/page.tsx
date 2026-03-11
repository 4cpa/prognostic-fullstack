import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

type QuestionCreate = {
  title: string;
  description: string;
  category?: string;
  region?: string | null;
  country?: string | null;
  resolve_at: string;
  resolution_criteria: string;
  resolution_source_policy?: string;
};

type ForecastRead = {
  id: string;
  question_id: string;
  created_at: string;
  probability: number; // erwartet 0..1 aus dem Backend
  confidence?: number | null; // 0..100
  method: string;
  method_version: string;
  explanation_md: string;
  inputs_hash: string;
};

function apiBase(): string {
  return process.env.API_BASE_URL || "http://backend:8000";
}

function humanizeSlug(slug: string): string {
  try {
    const decoded = decodeURIComponent(slug);
    return decoded.replace(/-/g, " ").trim();
  } catch {
    return slug.replace(/-/g, " ").trim();
  }
}

function toPercent(probability: number): string {
  const normalized =
    probability > 1 ? Math.min(Math.max(probability / 100, 0), 1) : Math.min(Math.max(probability, 0), 1);

  return `${(normalized * 100).toFixed(1)}%`;
}

function formatConfidence(confidence?: number | null): string | null {
  if (confidence == null || Number.isNaN(confidence)) {
    return null;
  }

  const normalized = Math.min(Math.max(confidence, 0), 100);
  return `${normalized.toFixed(1)}%`;
}

async function createQuestionFromSlug(slug: string): Promise<{ id: string }> {
  const base = apiBase();
  const title = humanizeSlug(slug);
  const resolveAt = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString();

  const payload: QuestionCreate = {
    title,
    description: `Auto-generierte Frage aus URL-Slug: "${slug}"`,
    category: "politics",
    region: null,
    country: null,
    resolve_at: resolveAt,
    resolution_criteria: "Auto-generated (to be refined).",
    resolution_source_policy: "official + 1 major wire (Reuters/AP/AFP)",
  };

  const res = await fetch(`${base}/questions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Fehler beim Erstellen der Frage (${res.status}): ${txt}`);
  }

  return res.json();
}

async function createForecast(questionId: string): Promise<ForecastRead> {
  const base = apiBase();

  const res = await fetch(`${base}/questions/${questionId}/forecast`, {
    method: "POST",
    cache: "no-store",
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Fehler beim Laden der Prognose (${res.status}): ${txt}`);
  }

  return res.json();
}

export default async function ForecastPage({
  params,
}: {
  params: Promise<{ slug?: string }> | { slug?: string };
}) {
  const resolved = await Promise.resolve(params);
  const slug = resolved?.slug;

  if (!slug || slug === "undefined") {
    notFound();
  }

  const q = await createQuestionFromSlug(slug);
  const f = await createForecast(q.id);

  return (
    <div className="min-h-screen bg-gray-50 p-10">
      <h1 className="mb-2 text-3xl font-bold">Prognose</h1>
      <p className="mb-8 text-gray-600">
        Slug: <span className="font-mono">{slug}</span> — Question ID:{" "}
        <span className="font-mono">{q.id}</span>
      </p>

      <div className="mb-8 max-w-2xl rounded-xl bg-white p-6 shadow-md">
        <p className="mb-4 text-xl font-semibold">
          Wahrscheinlichkeit: {toPercent(f.probability)}
        </p>

        {f.confidence != null && (
          <p className="mb-4 text-gray-700">Confidence: {formatConfidence(f.confidence)}</p>
        )}

        <p className="mb-4 text-sm text-gray-500">
          Methode: {f.method} ({f.method_version})
        </p>

        <div className="prose max-w-none">
          <pre className="whitespace-pre-wrap">{f.explanation_md}</pre>
        </div>
      </div>
    </div>
  );
}
