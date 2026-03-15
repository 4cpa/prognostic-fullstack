import Link from "next/link";
import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";
export const revalidate = 0;

type PageProps = {
  searchParams?: Promise<{ error?: string }> | { error?: string };
};

type QuestionCreateResponse = {
  id: string;
  slug?: string | null;
  title?: string | null;
  description?: string | null;
  resolve_at?: string | null;
  resolution_criteria?: string | null;
};

type ForecastCreateResponse = {
  question?: {
    id?: string | null;
    slug?: string | null;
    title?: string | null;
    question?: string | null;
  } | null;
  forecast?: {
    id?: string | null;
    question_id?: string | null;
    probability?: number | null;
    raw_probability?: number | null;
    calibrated_probability?: number | null;
    confidence?: number | null;
    summary?: string | null;
    explanation_md?: string | null;
    explanationMd?: string | null;
    direct_answer?: string | null;
    answer_label?: string | null;
    answer_confidence_band?: string | null;
    answer_rationale_short?: string | null;
    created_at?: string | null;
  } | null;
};

function getApiBaseUrl(): string {
  return (
    process.env.INTERNAL_API_BASE_URL ||
    process.env.NEXT_PUBLIC_INTERNAL_API_BASE_URL ||
    process.env.API_BASE_URL ||
    "http://backend:8000"
  ).replace(/\/+$/, "");
}

function stripMarkdown(input: string): string {
  return input
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1")
    .replace(/^\s*[-*+]\s+/gm, "")
    .replace(/\n{2,}/g, "\n")
    .trim();
}

function toErrorUrl(message: string): string {
  return `/?error=${encodeURIComponent(message)}`;
}

async function createQuestionAndForecast(formData: FormData): Promise<void> {
  "use server";

  const title = String(formData.get("title") || "").trim();
  const description = String(formData.get("description") || "").trim();
  const resolveAt = String(formData.get("resolve_at") || "").trim();
  const resolutionCriteria = String(formData.get("resolution_criteria") || "").trim();

  if (!title || !description || !resolveAt || !resolutionCriteria) {
    redirect(toErrorUrl("Bitte alle Felder ausfüllen."));
  }

  const baseUrl = getApiBaseUrl();

  let createdQuestion: QuestionCreateResponse;
  try {
    const questionRes = await fetch(`${baseUrl}/questions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      cache: "no-store",
      body: JSON.stringify({
        title,
        description,
        resolve_at: resolveAt,
        resolution_criteria: resolutionCriteria,
      }),
    });

    if (!questionRes.ok) {
      const text = await questionRes.text();
      redirect(toErrorUrl(`POST /questions failed: ${questionRes.status} ${text}`));
    }

    createdQuestion = (await questionRes.json()) as QuestionCreateResponse;
  } catch (error) {
    redirect(toErrorUrl(`POST /questions failed: ${String(error)}`));
  }

  const questionId = createdQuestion?.id;
  if (!questionId) {
    redirect(toErrorUrl("Question created, aber keine ID in der Antwort gefunden."));
  }

  let createdForecast: ForecastCreateResponse["forecast"] | null | undefined;
  let createdForecastQuestion: ForecastCreateResponse["question"] | null | undefined;

  try {
    const forecastRes = await fetch(
      `${baseUrl}/questions/${questionId}/forecast?method_version=v0.1.0`,
      {
        method: "POST",
        headers: {
          Accept: "application/json",
        },
        cache: "no-store",
      },
    );

    if (!forecastRes.ok) {
      const text = await forecastRes.text();
      redirect(
        toErrorUrl(
          `POST /api/questions/${questionId}/forecast?method_version=v0.1.0 failed: ${forecastRes.status} ${text}`,
        ),
      );
    }

    const forecastJson = (await forecastRes.json()) as ForecastCreateResponse;
    createdForecast = forecastJson?.forecast ?? null;
    createdForecastQuestion = forecastJson?.question ?? null;
  } catch (error) {
    redirect(toErrorUrl(`POST /forecast failed: ${String(error)}`));
  }

  const explanation =
    createdForecast?.explanation_md ??
    createdForecast?.explanationMd ??
    createdForecast?.summary ??
    "";

  const summaryText = stripMarkdown(explanation);

  const targetSlug =
    createdForecastQuestion?.slug ||
    createdQuestion.slug ||
    createdForecastQuestion?.id ||
    createdQuestion.id;

  if (targetSlug) {
    redirect(`/forecast/${targetSlug}`);
  }

  redirect(
    toErrorUrl(
      summaryText ||
        "Frage und Forecast wurden erzeugt, aber es konnte kein Ziel-Link bestimmt werden.",
    ),
  );
}

export default async function HomePage({ searchParams }: PageProps) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const error = resolvedSearchParams?.error
    ? decodeURIComponent(String(resolvedSearchParams.error))
    : null;

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-8">
          <Link href="/" className="text-sm font-medium text-slate-600 hover:text-slate-900">
            4cpa Prognostic
          </Link>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950">
            Neue Prognosefrage anlegen
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Frage erfassen, dann direkt einen Forecast erzeugen und zur Detailseite springen.
          </p>
        </div>

        {error ? (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {error}
          </div>
        ) : null}

        <form
          action={createQuestionAndForecast}
          className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <div>
            <label htmlFor="title" className="mb-2 block text-sm font-medium text-slate-900">
              Titel
            </label>
            <input
              id="title"
              name="title"
              type="text"
              required
              className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500"
              placeholder="Wird X bis Ende 2026 eintreten?"
            />
          </div>

          <div>
            <label htmlFor="description" className="mb-2 block text-sm font-medium text-slate-900">
              Beschreibung
            </label>
            <textarea
              id="description"
              name="description"
              required
              rows={4}
              className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500"
              placeholder="Kurze Beschreibung der Frage und des Kontexts."
            />
          </div>

          <div>
            <label htmlFor="resolve_at" className="mb-2 block text-sm font-medium text-slate-900">
              Resolve At
            </label>
            <input
              id="resolve_at"
              name="resolve_at"
              type="datetime-local"
              required
              className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none ring-0 focus:border-slate-500"
            />
          </div>

          <div>
            <label
              htmlFor="resolution_criteria"
              className="mb-2 block text-sm font-medium text-slate-900"
            >
              Resolution Criteria
            </label>
            <textarea
              id="resolution_criteria"
              name="resolution_criteria"
              required
              rows={4}
              className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500"
              placeholder="Wann gilt die Frage als Ja oder Nein?"
            />
          </div>

          <button
            type="submit"
            className="inline-flex rounded-xl bg-slate-900 px-5 py-3 text-sm font-medium text-white hover:bg-slate-800"
          >
            Frage anlegen und Forecast erzeugen
          </button>
        </form>
      </div>
    </main>
  );
}
