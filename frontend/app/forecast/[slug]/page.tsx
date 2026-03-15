import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";
export const revalidate = 0;

type RouteParams =
  | { slug: string }
  | Promise<{
      slug: string;
    }>;

type PageProps = {
  params: RouteParams;
};

type QuestionRecord = {
  id: number;
  slug: string;
  title?: string;
  question?: string;
  created_at?: string;
  createdAt?: string;
  resolved_at?: string | null;
  outcome?: string | null;
  is_resolved?: boolean;
};

type SourceRecord = {
  id?: number | string;
  title?: string | null;
  url?: string | null;
  domain?: string | null;
  published_at?: string | null;
  excerpt?: string | null;
  summary?: string | null;
  relevance_score?: number | null;
  weight?: number | null;
};

type ClaimRecord = {
  id?: number | string;
  text?: string | null;
  claim_text?: string | null;
  stance?: string | null;
  direction?: string | null;
  type?: string | null;
  claim_type?: string | null;
  confidence?: number | null;
  claim_confidence?: number | null;
  relevance_score?: number | null;
  relevance_weight?: number | null;
  weight?: number | null;
  final_weight?: number | null;
  source_title?: string | null;
  source_url?: string | null;
  explanation?: string | null;
};

type DiagnosticsRecord = Record<string, unknown>;

type RuntimeCalibrationMeta = {
  enabled?: boolean;
  record_count?: number;
  method?: string | null;
  bin_count?: number | null;
  min_bin_count?: number | null;
  notes?: string[] | null;
  [key: string]: unknown;
};

type ForecastRecord = {
  id?: number;
  probability?: number | null;
  raw_probability?: number | null;
  calibrated_probability?: number | null;
  confidence?: number | null;
  explanation_md?: string | null;
  summary?: string | null;
  created_at?: string | null;
  runtime_calibration_meta?: RuntimeCalibrationMeta | null;
  calibration_signals?: Record<string, unknown> | null;
  diagnostics?: DiagnosticsRecord | null;
  direct_answer?: string | null;
  answer_label?: string | null;
  answer_confidence_band?: string | null;
  answer_rationale_short?: string | null;
};

type FullForecastResponse = {
  question?: QuestionRecord;
  forecast?: ForecastRecord;
  summary?: string | null;
  sources?: SourceRecord[];
  claims?: ClaimRecord[];
  top_pro_claims?: ClaimRecord[];
  top_contra_claims?: ClaimRecord[];
  top_uncertainties?: ClaimRecord[];
  diagnostics?: DiagnosticsRecord | null;
  raw_probability?: number | null;
  calibrated_probability?: number | null;
  runtime_calibration_meta?: RuntimeCalibrationMeta | null;
  calibration_signals?: Record<string, unknown> | null;
  direct_answer?: string | null;
  answer_label?: string | null;
  answer_confidence_band?: string | null;
  answer_rationale_short?: string | null;
};

function getApiBaseUrl(): string {
  return (
    process.env.INTERNAL_API_BASE_URL ||
    process.env.NEXT_PUBLIC_INTERNAL_API_BASE_URL ||
    process.env.API_BASE_URL ||
    "http://backend:8000"
  ).replace(/\/+$/, "");
}

async function apiFetch<T>(path: string): Promise<T | null> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${path}`;

  try {
    const response = await fetch(url, {
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    });

    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText} (${url})`);
    }

    return (await response.json()) as T;
  } catch (error) {
    console.error("apiFetch failed", { url, error });
    return null;
  }
}

function normalizeQuestion(payload: unknown): QuestionRecord | null {
  if (!payload) return null;

  if (Array.isArray(payload) && payload.length > 0) {
    const first = payload[0];
    if (first && typeof first === "object" && typeof (first as { id?: unknown }).id === "number") {
      return first as QuestionRecord;
    }
  }

  if (typeof payload !== "object") return null;

  const data = payload as Record<string, unknown>;

  if (typeof data.id === "number") {
    return data as QuestionRecord;
  }

  if (Array.isArray(data.items) && data.items.length > 0) {
    const first = data.items[0];
    if (first && typeof first === "object" && typeof (first as { id?: unknown }).id === "number") {
      return first as QuestionRecord;
    }
  }

  if (Array.isArray(data.questions) && data.questions.length > 0) {
    const first = data.questions[0];
    if (first && typeof first === "object" && typeof (first as { id?: unknown }).id === "number") {
      return first as QuestionRecord;
    }
  }

  return null;
}

async function getQuestionBySlug(slug: string): Promise<QuestionRecord | null> {
  const encodedSlug = encodeURIComponent(slug);

  const candidates = [
    `/questions/slug/${encodedSlug}`,
    `/questions/by-slug/${encodedSlug}`,
    `/questions/${encodedSlug}`,
    `/questions?slug=${encodedSlug}`,
    `/questions?search=${encodedSlug}`,
  ];

  for (const path of candidates) {
    const payload = await apiFetch<unknown>(path);
    const question = normalizeQuestion(payload);
    if (question?.id) {
      return question;
    }
  }

  return null;
}

async function getFullForecast(questionId: number): Promise<FullForecastResponse | null> {
  return await apiFetch<FullForecastResponse>(`/questions/${questionId}/forecast/latest/full`);
}

function toDisplayQuestion(question?: QuestionRecord | null): string {
  return question?.title || question?.question || "Forecast";
}

function formatPercent(value?: number | null): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  const normalized = value <= 1 ? value * 100 : value;
  return `${normalized.toFixed(1)}%`;
}

function formatDate(value?: string | null): string {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("de-CH", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function scoreText(value?: number | null): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return value.toFixed(2);
}

function getClaimText(claim: ClaimRecord): string {
  return claim.text || claim.claim_text || "—";
}

function getClaimDirection(claim: ClaimRecord): string | null {
  return claim.stance || claim.direction || null;
}

function getClaimType(claim: ClaimRecord): string | null {
  return claim.type || claim.claim_type || null;
}

function getClaimConfidence(claim: ClaimRecord): number | null {
  return claim.confidence ?? claim.claim_confidence ?? null;
}

function getClaimRelevance(claim: ClaimRecord): number | null {
  return claim.relevance_score ?? claim.relevance_weight ?? null;
}

function getClaimWeight(claim: ClaimRecord): number | null {
  return claim.weight ?? claim.final_weight ?? null;
}

function objectEntries(record: Record<string, unknown> | null | undefined): Array<[string, unknown]> {
  if (!record || typeof record !== "object") return [];
  return Object.entries(record).filter(([, value]) => value !== null && value !== undefined);
}

function renderUnknown(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function answerTone(
  label?: string | null,
): "positive" | "negative" | "neutral" | "muted" {
  switch (label) {
    case "yes":
    case "lean_yes":
      return "positive";
    case "no":
    case "lean_no":
      return "negative";
    case "uncertain":
      return "neutral";
    default:
      return "muted";
  }
}

function badgeText(label?: string | null): string {
  switch (label) {
    case "yes":
      return "Ja";
    case "lean_yes":
      return "Eher Ja";
    case "no":
      return "Nein";
    case "lean_no":
      return "Eher Nein";
    case "uncertain":
      return "Unklar";
    default:
      return "Keine klare Antwort";
  }
}

function toneClasses(tone: "positive" | "negative" | "neutral" | "muted" | "default"): string {
  if (tone === "positive") return "bg-green-100 text-green-800 border-green-200";
  if (tone === "negative") return "bg-red-100 text-red-800 border-red-200";
  if (tone === "neutral") return "bg-amber-100 text-amber-800 border-amber-200";
  if (tone === "muted") return "bg-slate-100 text-slate-700 border-slate-200";
  return "bg-blue-100 text-blue-800 border-blue-200";
}

function cardToneClasses(tone: "positive" | "negative" | "neutral" | "muted"): string {
  if (tone === "positive") return "border-green-200 bg-green-50";
  if (tone === "negative") return "border-red-200 bg-red-50";
  if (tone === "neutral") return "border-amber-200 bg-amber-50";
  return "border-slate-200 bg-slate-50";
}

function Badge({
  children,
  tone = "default",
}: {
  children: React.ReactNode;
  tone?: "default" | "positive" | "negative" | "neutral" | "muted";
}) {
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${toneClasses(tone)}`}
    >
      {children}
    </span>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-slate-900">{title}</h2>
      {children}
    </section>
  );
}

function ClaimList({
  claims,
  emptyText,
  tone,
}: {
  claims?: ClaimRecord[];
  emptyText: string;
  tone: "positive" | "negative" | "muted";
}) {
  if (!claims || claims.length === 0) {
    return <p className="text-sm text-slate-500">{emptyText}</p>;
  }

  return (
    <div className="space-y-4">
      {claims.map((claim, index) => (
        <article
          key={String(claim.id ?? `${tone}-${index}`)}
          className="rounded-xl border border-slate-200 bg-slate-50 p-4"
        >
          <div className="mb-3 flex flex-wrap items-center gap-2">
            {getClaimDirection(claim) ? <Badge tone={tone}>{getClaimDirection(claim)}</Badge> : null}
            {getClaimType(claim) ? <Badge tone="muted">{getClaimType(claim)}</Badge> : null}
            <Badge tone="muted">Confidence {scoreText(getClaimConfidence(claim))}</Badge>
            <Badge tone="muted">Relevance {scoreText(getClaimRelevance(claim))}</Badge>
            <Badge tone="muted">Weight {scoreText(getClaimWeight(claim))}</Badge>
          </div>

          <p className="text-sm leading-6 text-slate-800">{getClaimText(claim)}</p>

          {claim.explanation ? (
            <p className="mt-3 text-sm leading-6 text-slate-600">{claim.explanation}</p>
          ) : null}

          {claim.source_title || claim.source_url ? (
            <div className="mt-3 text-xs text-slate-500">
              Quelle:{" "}
              {claim.source_url ? (
                <a
                  href={claim.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="underline decoration-slate-300 underline-offset-2 hover:text-slate-700"
                >
                  {claim.source_title || claim.source_url}
                </a>
              ) : (
                claim.source_title
              )}
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}

function SourceList({ sources }: { sources?: SourceRecord[] }) {
  if (!sources || sources.length === 0) {
    return <p className="text-sm text-slate-500">Keine Quellen vorhanden.</p>;
  }

  return (
    <div className="space-y-4">
      {sources.map((source, index) => (
        <article
          key={String(source.id ?? `source-${index}`)}
          className="rounded-xl border border-slate-200 bg-slate-50 p-4"
        >
          <div className="flex flex-wrap items-center gap-2">
            {source.domain ? <Badge tone="muted">{source.domain}</Badge> : null}
            <Badge tone="muted">Relevance {scoreText(source.relevance_score)}</Badge>
            <Badge tone="muted">Weight {scoreText(source.weight)}</Badge>
          </div>

          <h3 className="mt-3 text-sm font-semibold text-slate-900">
            {source.url ? (
              <a
                href={source.url}
                target="_blank"
                rel="noreferrer"
                className="underline decoration-slate-300 underline-offset-2 hover:text-slate-700"
              >
                {source.title || source.url}
              </a>
            ) : (
              source.title || "Ohne Titel"
            )}
          </h3>

          <div className="mt-2 text-xs text-slate-500">
            Veröffentlicht: {formatDate(source.published_at)}
          </div>

          {source.summary || source.excerpt ? (
            <p className="mt-3 text-sm leading-6 text-slate-700">
              {source.summary || source.excerpt}
            </p>
          ) : null}
        </article>
      ))}
    </div>
  );
}

function DiagnosticsTable({
  title,
  data,
}: {
  title: string;
  data?: Record<string, unknown> | null;
}) {
  const entries = objectEntries(data);

  return (
    <Section title={title}>
      {entries.length === 0 ? (
        <p className="text-sm text-slate-500">Keine Diagnostik vorhanden.</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <tbody className="divide-y divide-slate-200 bg-white">
              {entries.map(([key, value]) => (
                <tr key={key}>
                  <td className="w-1/3 bg-slate-50 px-4 py-3 font-medium text-slate-700">{key}</td>
                  <td className="px-4 py-3 text-slate-800">{renderUnknown(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  );
}

export default async function ForecastDetailPage({ params }: PageProps) {
  const resolvedParams = await Promise.resolve(params);
  const slug = resolvedParams?.slug;

  if (!slug) {
    notFound();
  }

  const question = await getQuestionBySlug(slug);
  if (!question?.id) {
    notFound();
  }

  const full = await getFullForecast(question.id);
  if (!full) {
    notFound();
  }

  const forecast = full.forecast ?? {};
  const runtimeCalibrationMeta =
    full.runtime_calibration_meta ?? forecast.runtime_calibration_meta ?? null;
  const diagnostics = full.diagnostics ?? forecast.diagnostics ?? null;
  const calibrationSignals = full.calibration_signals ?? forecast.calibration_signals ?? null;

  const persistedProbability = forecast.probability;
  const rawProbability = full.raw_probability ?? forecast.raw_probability;
  const calibratedProbability = full.calibrated_probability ?? forecast.calibrated_probability;

  const directAnswer = full.direct_answer ?? forecast.direct_answer ?? null;
  const answerLabel = full.answer_label ?? forecast.answer_label ?? null;
  const answerConfidenceBand =
    full.answer_confidence_band ?? forecast.answer_confidence_band ?? null;
  const answerRationaleShort =
    full.answer_rationale_short ?? forecast.answer_rationale_short ?? null;

  const questionData = full.question ?? question;
  const questionText = toDisplayQuestion(questionData);
  const answerToneValue = answerTone(answerLabel);

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Badge>Forecast Detail</Badge>
            {questionData?.is_resolved ? (
              <Badge tone="muted">Resolved</Badge>
            ) : (
              <Badge tone="default">Open</Badge>
            )}
            {questionData?.outcome ? <Badge tone="muted">Outcome {questionData.outcome}</Badge> : null}
          </div>

          <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
            {questionText}
          </h1>

          <div
            className={`mt-6 rounded-2xl border p-5 ${cardToneClasses(answerToneValue)}`}
          >
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Badge tone={answerToneValue}>{badgeText(answerLabel)}</Badge>
              {answerConfidenceBand ? <Badge tone="muted">{answerConfidenceBand}</Badge> : null}
            </div>

            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Direkte Antwort
            </div>

            <p className="mt-2 text-lg font-semibold leading-7 text-slate-950">
              {directAnswer || "Noch keine direkte Antwort verfügbar."}
            </p>

            {answerRationaleShort ? (
              <p className="mt-3 text-sm leading-6 text-slate-700">{answerRationaleShort}</p>
            ) : null}
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Persistierte Wahrscheinlichkeit
              </div>
              <div className="mt-2 text-3xl font-semibold text-slate-950">
                {formatPercent(persistedProbability)}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Raw Probability
              </div>
              <div className="mt-2 text-3xl font-semibold text-slate-950">
                {formatPercent(rawProbability)}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Calibrated Probability
              </div>
              <div className="mt-2 text-3xl font-semibold text-slate-950">
                {formatPercent(calibratedProbability)}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Confidence
              </div>
              <div className="mt-2 text-3xl font-semibold text-slate-950">
                {scoreText(forecast.confidence)}
              </div>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-600">
            <span>Frage-ID: {questionData.id}</span>
            <span>Slug: {questionData.slug}</span>
            <span>Forecast erstellt: {formatDate(forecast.created_at)}</span>
            <span>Frage erstellt: {formatDate(questionData.created_at ?? questionData.createdAt)}</span>
            <span>Resolved am: {formatDate(questionData.resolved_at)}</span>
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-3">
          <div className="space-y-6 xl:col-span-2">
            <Section title="Summary">
              <p className="whitespace-pre-wrap text-sm leading-7 text-slate-800">
                {full.summary || forecast.summary || forecast.explanation_md || "Keine Zusammenfassung vorhanden."}
              </p>
            </Section>

            <Section title="Top Pro Claims">
              <ClaimList
                claims={full.top_pro_claims}
                emptyText="Keine Pro-Claims vorhanden."
                tone="positive"
              />
            </Section>

            <Section title="Top Contra Claims">
              <ClaimList
                claims={full.top_contra_claims}
                emptyText="Keine Contra-Claims vorhanden."
                tone="negative"
              />
            </Section>

            <Section title="Top Uncertainties">
              <ClaimList
                claims={full.top_uncertainties}
                emptyText="Keine Unsicherheiten vorhanden."
                tone="muted"
              />
            </Section>

            <Section title="Alle Claims">
              <ClaimList
                claims={full.claims}
                emptyText="Keine Claims vorhanden."
                tone="muted"
              />
            </Section>

            <Section title="Quellen">
              <SourceList sources={full.sources} />
            </Section>
          </div>

          <div className="space-y-6">
            <Section title="Antwort-Metadaten">
              <div className="space-y-3 text-sm text-slate-800">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-slate-600">Label:</span>
                  <Badge tone={answerToneValue}>{badgeText(answerLabel)}</Badge>
                </div>

                <div>
                  <span className="font-medium text-slate-600">Confidence Band:</span>{" "}
                  {answerConfidenceBand || "—"}
                </div>

                <div>
                  <span className="font-medium text-slate-600">Kurzbegründung:</span>{" "}
                  {answerRationaleShort || "—"}
                </div>
              </div>
            </Section>

            <Section title="Runtime Calibration Meta">
              {objectEntries(runtimeCalibrationMeta).length === 0 ? (
                <p className="text-sm text-slate-500">Keine Runtime-Kalibrierungsdaten vorhanden.</p>
              ) : (
                <div className="overflow-hidden rounded-xl border border-slate-200">
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <tbody className="divide-y divide-slate-200 bg-white">
                      {objectEntries(runtimeCalibrationMeta).map(([key, value]) => (
                        <tr key={key}>
                          <td className="w-1/2 bg-slate-50 px-4 py-3 font-medium text-slate-700">
                            {key}
                          </td>
                          <td className="px-4 py-3 text-slate-800">{renderUnknown(value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Section>

            <DiagnosticsTable title="Diagnostics" data={diagnostics} />
            <DiagnosticsTable title="Calibration Signals" data={calibrationSignals} />
          </div>
        </div>
      </div>
    </main>
  );
}
