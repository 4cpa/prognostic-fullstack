import { notFound } from "next/navigation";

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
  probability: number;
  confidence?: number | null;
  method: string;
  method_version: string;
  explanation_md: string;
  inputs_hash: string;
};

function apiBase(): string {
  // SSR im Container -> backend service
  return process.env.API_BASE_URL || "http://backend:8000";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";
export const dynamicParams = true;
export const revalidate = 0;

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
  probability: number;
  confidence?: number | null;
  method: string;
  method_version: string;
  explanation_md: string;
  inputs_hash: string;
};

function apiBase(): string {
  // SSR im Container -> backend service
  return process.env.API_BASE_URL || "http://backend:8000";
}

function humanizeSlug(slug: string) {
  try {
    const decoded = decodeURIComponent(slug);
    return decoded.replace(/-/g, " ").trim();
  } catch {
    return slug.replace(/-/g, " ").trim();
  }
}

async function createQuestionFromSlug(slug: string): Promise<{ id: string }> {
  const base = apiBase();
  const title = humanizeSlug(slug);

  // default: 1 Jahr in der Zukunft
  const resolveAt = new Date(
    Date.now() + 365 * 24 * 60 * 60 * 1000
  ).toISOString();

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
  params: { slug?: string };
}) {
  const slug = params?.slug;

  // verhindert /forecast/undefined + stoppt SSR-Loops sauber
  if (!slug || slug === "undefined") notFound();

  // NOTE: Ohne "slug -> question_id" Mapping erzeugen wir vorerst pro slug eine neue Question.
  const q = await createQuestionFromSlug(slug);
  const f = await createForecast(q.id);

  return (
    <div className="min-h-screen p-10 bg-gray-50">
      <h1 className="text-3xl font-bold mb-2">Prognose</h1>
      <p className="text-gray-600 mb-8">
        Slug: <span className="font-mono">{slug}</span> — Question ID:{" "}
        <span className="font-mono">{q.id}</span>
      </p>

      <div className="bg-white p-6 rounded-xl shadow-md max-w-2xl mb-8">
        <p className="text-xl font-semibold mb-4">
          Wahrscheinlichkeit: {f.probability}%
        </p>

        {f.confidence != null && (
          <p className="text-gray-700 mb-4">Confidence: {f.confidence}</p>
        )}

        <p className="text-sm text-gray-500 mb-4">
          Methode: {f.method} ({f.method_version})
        </p>

        <div className="prose max-w-none">
          {/* explanation_md ist Markdown; fürs Erste plain anzeigen */}
          <pre className="whitespace-pre-wrap">{f.explanation_md}</pre>
        </div>
      </div>
    </div>
  );
}
