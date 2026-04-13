import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";
export const revalidate = 0;

type RouteParams =
  | { slug: string }
  | Promise<{ slug: string }>;

type PageProps = {
  params: RouteParams;
};

type QuestionRecord = {
  id: string;
  slug?: string | null;
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

// ── Datenzugriff ────────────────────────────────────────────────────────────

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
      headers: { Accept: "application/json" },
    });

    if (response.status === 404) return null;

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText} (${url})`);
    }

    return (await response.json()) as T;
  } catch (error) {
    console.error("apiFetch failed", { url, error });
    return null;
  }
}

function hasId(obj: unknown): obj is QuestionRecord {
  if (!obj || typeof obj !== "object") return false;
  const id = (obj as Record<string, unknown>).id;
  return typeof id === "string" && id.length > 0;
}

function normalizeQuestion(payload: unknown): QuestionRecord | null {
  if (!payload) return null;

  if (Array.isArray(payload) && payload.length > 0) {
    const first = payload[0];
    if (hasId(first)) return first;
  }

  if (typeof payload !== "object") return null;

  const data = payload as Record<string, unknown>;

  if (hasId(data)) return data as QuestionRecord;

  if (Array.isArray(data.items) && data.items.length > 0) {
    const first = data.items[0];
    if (hasId(first)) return first;
  }

  if (Array.isArray(data.questions) && data.questions.length > 0) {
    const first = data.questions[0];
    if (hasId(first)) return first;
  }

  return null;
}

async function getQuestionBySlug(slug: string): Promise<QuestionRecord | null> {
  const encodedSlug = encodeURIComponent(slug);

  for (const path of [
    `/questions/slug/${encodedSlug}`,
    `/questions/by-slug/${encodedSlug}`,
    `/questions/${encodedSlug}`,
    `/questions?slug=${encodedSlug}`,
    `/questions?search=${encodedSlug}`,
  ]) {
    const payload = await apiFetch<unknown>(path);
    const question = normalizeQuestion(payload);
    if (question?.id) return question;
  }

  return null;
}

async function getFullForecast(questionId: string): Promise<FullForecastResponse | null> {
  return apiFetch<FullForecastResponse>(`/questions/${questionId}/forecast/latest/full`);
}

// ── Hilfsfunktionen ─────────────────────────────────────────────────────────

function toDisplayQuestion(question?: QuestionRecord | null): string {
  return question?.title || question?.question || "Forecast";
}

/** Wahrscheinlichkeit als gerundeten Prozentwert (z. B. 67.3) */
function toPercentValue(value?: number | null): number | null {
  if (typeof value !== "number" || Number.isNaN(value)) return null;
  const normalized = value <= 1 ? value * 100 : value;
  return Math.round(normalized * 10) / 10;
}

/** ISO-Datumstring als lesbares Datum + maschinenlesbares datetime-Attribut */
function parseDate(value?: string | null): { display: string; iso: string } | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;

  return {
    display: new Intl.DateTimeFormat("de-CH", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(date),
    iso: date.toISOString(),
  };
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

function answerTone(label?: string | null): "positive" | "negative" | "neutral" | "muted" {
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
    case "yes":      return "Ja";
    case "lean_yes": return "Eher Ja";
    case "no":       return "Nein";
    case "lean_no":  return "Eher Nein";
    case "uncertain": return "Unklar";
    default:         return "Keine klare Antwort";
  }
}

function toneClasses(tone: "positive" | "negative" | "neutral" | "muted" | "default"): string {
  if (tone === "positive") return "bg-green-100 text-green-900 border-green-300";
  if (tone === "negative") return "bg-red-100 text-red-900 border-red-300";
  if (tone === "neutral")  return "bg-amber-100 text-amber-900 border-amber-300";
  if (tone === "muted")    return "bg-slate-100 text-slate-800 border-slate-300";
  return "bg-blue-100 text-blue-900 border-blue-300";
}

function cardToneClasses(tone: "positive" | "negative" | "neutral" | "muted"): string {
  if (tone === "positive") return "border-green-200 bg-green-50";
  if (tone === "negative") return "border-red-200 bg-red-50";
  if (tone === "neutral")  return "border-amber-200 bg-amber-50";
  return "border-slate-200 bg-slate-50";
}

// ── Komponenten ─────────────────────────────────────────────────────────────

function Badge({
  children,
  tone = "default",
}: {
  children: React.ReactNode;
  tone?: "default" | "positive" | "negative" | "neutral" | "muted";
}) {
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${toneClasses(tone)}`}>
      {children}
    </span>
  );
}

function Section({
  title,
  headingLevel = "h2",
  children,
}: {
  title: string;
  headingLevel?: "h2" | "h3";
  children: React.ReactNode;
}) {
  const Heading = headingLevel;
  return (
    <section
      aria-labelledby={`section-${title.replace(/\s+/g, "-").toLowerCase()}`}
      className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <Heading
        id={`section-${title.replace(/\s+/g, "-").toLowerCase()}`}
        className="mb-4 text-lg font-semibold text-slate-900"
      >
        {title}
      </Heading>
      {children}
    </section>
  );
}

/** Externer Link mit sichtbarem + screenreader-kompatiblem Hinweis */
function ExternalLink({
  href,
  children,
  className,
}: {
  href: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={className ?? "underline decoration-slate-300 underline-offset-2 hover:text-slate-700"}
    >
      {children}
      {/* Screenreader-Hinweis: öffnet in neuem Tab */}
      <span className="sr-only">&nbsp;(öffnet in neuem Tab)</span>
    </a>
  );
}

/** Datum-Element mit maschinenlesbarem datetime-Attribut */
function DateDisplay({ value }: { value?: string | null }) {
  const parsed = parseDate(value);
  if (!parsed) return <span>—</span>;
  return <time dateTime={parsed.iso}>{parsed.display}</time>;
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
    return <p className="text-sm text-slate-600">{emptyText}</p>;
  }

  const toneLabel =
    tone === "positive" ? "Pro" : tone === "negative" ? "Contra" : "Unsicherheit";

  return (
    <ul className="space-y-4" aria-label={`${toneLabel}-Claims`}>
      {claims.map((claim, index) => {
        const direction = getClaimDirection(claim);
        const type = getClaimType(claim);
        const confidence = getClaimConfidence(claim);
        const relevance = getClaimRelevance(claim);
        const weight = getClaimWeight(claim);

        return (
          <li
            key={String(claim.id ?? `${tone}-${index}`)}
            className="rounded-xl border border-slate-200 bg-slate-50 p-4"
          >
            {/* Metadaten als Definition List */}
            <dl className="mb-3 flex flex-wrap items-center gap-2 text-xs">
              {direction && (
                <div className="flex items-center gap-1">
                  <dt className="sr-only">Richtung:</dt>
                  <dd><Badge tone={tone}>{direction}</Badge></dd>
                </div>
              )}
              {type && (
                <div className="flex items-center gap-1">
                  <dt className="sr-only">Typ:</dt>
                  <dd><Badge tone="muted">{type}</Badge></dd>
                </div>
              )}
              <div className="flex items-center gap-1">
                <dt className="sr-only">Konfidenz:</dt>
                <dd>
                  <Badge tone="muted">
                    <span aria-label={`Konfidenz ${scoreText(confidence)}`}>
                      Confidence {scoreText(confidence)}
                    </span>
                  </Badge>
                </dd>
              </div>
              <div className="flex items-center gap-1">
                <dt className="sr-only">Relevanz:</dt>
                <dd>
                  <Badge tone="muted">
                    <span aria-label={`Relevanz ${scoreText(relevance)}`}>
                      Relevance {scoreText(relevance)}
                    </span>
                  </Badge>
                </dd>
              </div>
              <div className="flex items-center gap-1">
                <dt className="sr-only">Gewichtung:</dt>
                <dd>
                  <Badge tone="muted">
                    <span aria-label={`Gewichtung ${scoreText(weight)}`}>
                      Weight {scoreText(weight)}
                    </span>
                  </Badge>
                </dd>
              </div>
            </dl>

            <p className="text-sm leading-6 text-slate-800">{getClaimText(claim)}</p>

            {claim.explanation && (
              <p className="mt-3 text-sm leading-6 text-slate-600">{claim.explanation}</p>
            )}

            {(claim.source_title || claim.source_url) && (
              <p className="mt-3 text-xs text-slate-500">
                <span className="font-medium">Quelle: </span>
                {claim.source_url ? (
                  <ExternalLink href={claim.source_url}>
                    {claim.source_title || claim.source_url}
                  </ExternalLink>
                ) : (
                  claim.source_title
                )}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function SourceList({ sources }: { sources?: SourceRecord[] }) {
  if (!sources || sources.length === 0) {
    return <p className="text-sm text-slate-600">Keine Quellen vorhanden.</p>;
  }

  return (
    <ul className="space-y-4" aria-label="Analysierte Quellen">
      {sources.map((source, index) => (
        <li
          key={String(source.id ?? `source-${index}`)}
          className="rounded-xl border border-slate-200 bg-slate-50 p-4"
        >
          <dl className="flex flex-wrap items-center gap-2 text-xs">
            {source.domain && (
              <div>
                <dt className="sr-only">Domain:</dt>
                <dd><Badge tone="muted">{source.domain}</Badge></dd>
              </div>
            )}
            <div>
              <dt className="sr-only">Relevanz:</dt>
              <dd>
                <Badge tone="muted">
                  <span aria-label={`Relevanz ${scoreText(source.relevance_score)}`}>
                    Relevance {scoreText(source.relevance_score)}
                  </span>
                </Badge>
              </dd>
            </div>
            <div>
              <dt className="sr-only">Gewichtung:</dt>
              <dd>
                <Badge tone="muted">
                  <span aria-label={`Gewichtung ${scoreText(source.weight)}`}>
                    Weight {scoreText(source.weight)}
                  </span>
                </Badge>
              </dd>
            </div>
          </dl>

          <h3 className="mt-3 text-sm font-semibold text-slate-900">
            {source.url ? (
              <ExternalLink href={source.url}>
                {source.title || source.url}
              </ExternalLink>
            ) : (
              source.title || "Ohne Titel"
            )}
          </h3>

          <p className="mt-2 text-xs text-slate-500">
            <span className="font-medium">Veröffentlicht: </span>
            <DateDisplay value={source.published_at} />
          </p>

          {(source.summary || source.excerpt) && (
            <p className="mt-3 text-sm leading-6 text-slate-700">
              {source.summary || source.excerpt}
            </p>
          )}
        </li>
      ))}
    </ul>
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
        <p className="text-sm text-slate-600">Keine Daten vorhanden.</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <caption className="sr-only">{title}</caption>
            <tbody className="divide-y divide-slate-200 bg-white">
              {entries.map(([key, value]) => (
                <tr key={key}>
                  <th
                    scope="row"
                    className="w-1/3 bg-slate-50 px-4 py-3 text-left font-medium text-slate-700"
                  >
                    {key}
                  </th>
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

// ── Seite ───────────────────────────────────────────────────────────────────

export default async function ForecastDetailPage({ params }: PageProps) {
  const resolvedParams = await Promise.resolve(params);
  const slug = resolvedParams?.slug;

  if (!slug) notFound();

  const question = await getQuestionBySlug(slug);
  if (!question?.id) notFound();

  const full = await getFullForecast(question.id);
  if (!full) notFound();

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
  const answerConfidenceBand = full.answer_confidence_band ?? forecast.answer_confidence_band ?? null;
  const answerRationaleShort = full.answer_rationale_short ?? forecast.answer_rationale_short ?? null;

  const questionData = full.question ?? question;
  const questionText = toDisplayQuestion(questionData);
  const answerToneValue = answerTone(answerLabel);

  return (
    <main id="main-content" className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">

        {/* ── Kopfbereich ── */}
        <header
          aria-label="Forecast-Übersicht"
          className="mb-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          {/* Status-Badges */}
          <div className="mb-4 flex flex-wrap items-center gap-2" aria-label="Status">
            <Badge>Forecast Detail</Badge>
            {questionData?.is_resolved ? (
              <Badge tone="muted">Aufgelöst</Badge>
            ) : (
              <Badge tone="default">Offen</Badge>
            )}
            {questionData?.outcome && (
              <Badge tone="muted">Ergebnis: {questionData.outcome}</Badge>
            )}
          </div>

          <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
            {questionText}
          </h1>

          {/* Direkte Antwort */}
          <div
            className={`mt-6 rounded-2xl border p-5 ${cardToneClasses(answerToneValue)}`}
            aria-label="Direkte Antwort"
          >
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Badge tone={answerToneValue}>{badgeText(answerLabel)}</Badge>
              {answerConfidenceBand && (
                <Badge tone="muted">{answerConfidenceBand}</Badge>
              )}
            </div>

            <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
              Direkte Antwort
            </p>

            <p className="mt-2 text-lg font-semibold leading-7 text-slate-950">
              {directAnswer || "Noch keine direkte Antwort verfügbar."}
            </p>

            {answerRationaleShort && (
              <p className="mt-3 text-sm leading-6 text-slate-700">{answerRationaleShort}</p>
            )}
          </div>

          {/* Wahrscheinlichkeits-Kacheln als semantische Definition List */}
          <dl className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[
              {
                label: "Wahrscheinlichkeit",
                value: persistedProbability,
                pct: toPercentValue(persistedProbability),
              },
              {
                label: "Rohwert",
                value: rawProbability,
                pct: toPercentValue(rawProbability),
              },
              {
                label: "Kalibriert",
                value: calibratedProbability,
                pct: toPercentValue(calibratedProbability),
              },
              {
                label: "Konfidenz",
                value: forecast.confidence,
                pct: null,
                text: scoreText(forecast.confidence),
              },
            ].map(({ label, pct, text }) => (
              <div
                key={label}
                className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
              >
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                  {label}
                </dt>
                <dd
                  className="mt-2 text-3xl font-semibold text-slate-950"
                  aria-label={
                    pct !== null
                      ? `${label}: ${pct} Prozent`
                      : `${label}: ${text ?? "—"}`
                  }
                >
                  {pct !== null ? `${pct} %` : (text ?? "—")}
                </dd>
              </div>
            ))}
          </dl>

          {/* Metadaten */}
          <dl className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600">
            <div className="flex gap-1">
              <dt className="font-medium">Frage-ID:</dt>
              <dd>{questionData.id}</dd>
            </div>
            <div className="flex gap-1">
              <dt className="font-medium">Slug:</dt>
              <dd>{questionData.slug}</dd>
            </div>
            <div className="flex gap-1">
              <dt className="font-medium">Forecast erstellt:</dt>
              <dd><DateDisplay value={forecast.created_at} /></dd>
            </div>
            <div className="flex gap-1">
              <dt className="font-medium">Frage erstellt:</dt>
              <dd><DateDisplay value={questionData.created_at ?? questionData.createdAt} /></dd>
            </div>
            {questionData.resolved_at && (
              <div className="flex gap-1">
                <dt className="font-medium">Aufgelöst am:</dt>
                <dd><DateDisplay value={questionData.resolved_at} /></dd>
              </div>
            )}
          </dl>
        </header>

        {/* ── Hauptinhalt ── */}
        <div className="grid gap-6 xl:grid-cols-3">
          <div className="space-y-6 xl:col-span-2">
            <Section title="Zusammenfassung">
              <p className="whitespace-pre-wrap text-sm leading-7 text-slate-800">
                {full.summary || forecast.summary || forecast.explanation_md ||
                  "Keine Zusammenfassung vorhanden."}
              </p>
            </Section>

            <Section title="Pro-Argumente">
              <ClaimList
                claims={full.top_pro_claims}
                emptyText="Keine Pro-Argumente vorhanden."
                tone="positive"
              />
            </Section>

            <Section title="Contra-Argumente">
              <ClaimList
                claims={full.top_contra_claims}
                emptyText="Keine Contra-Argumente vorhanden."
                tone="negative"
              />
            </Section>

            <Section title="Unsicherheiten">
              <ClaimList
                claims={full.top_uncertainties}
                emptyText="Keine Unsicherheiten vorhanden."
                tone="muted"
              />
            </Section>

            <Section title="Alle Argumente">
              <ClaimList
                claims={full.claims}
                emptyText="Keine Argumente vorhanden."
                tone="muted"
              />
            </Section>

            <Section title="Quellen">
              <SourceList sources={full.sources} />
            </Section>
          </div>

          <div className="space-y-6">
            <Section title="Antwort-Details">
              <dl className="space-y-3 text-sm text-slate-800">
                <div>
                  <dt className="font-semibold text-slate-600">Bewertung</dt>
                  <dd className="mt-1">
                    <Badge tone={answerToneValue}>{badgeText(answerLabel)}</Badge>
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold text-slate-600">Konfidenzband</dt>
                  <dd className="mt-1">{answerConfidenceBand || "—"}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-slate-600">Kurzbegründung</dt>
                  <dd className="mt-1">{answerRationaleShort || "—"}</dd>
                </div>
              </dl>
            </Section>

            <Section title="Laufzeit-Kalibrierung">
              {objectEntries(runtimeCalibrationMeta).length === 0 ? (
                <p className="text-sm text-slate-600">Keine Kalibrierungsdaten vorhanden.</p>
              ) : (
                <div className="overflow-hidden rounded-xl border border-slate-200">
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <caption className="sr-only">Laufzeit-Kalibrierungsmetadaten</caption>
                    <tbody className="divide-y divide-slate-200 bg-white">
                      {objectEntries(runtimeCalibrationMeta).map(([key, value]) => (
                        <tr key={key}>
                          <th
                            scope="row"
                            className="w-1/2 bg-slate-50 px-4 py-3 text-left font-medium text-slate-700"
                          >
                            {key}
                          </th>
                          <td className="px-4 py-3 text-slate-800">{renderUnknown(value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Section>

            <DiagnosticsTable title="Diagnostics" data={diagnostics} />
            <DiagnosticsTable title="Kalibrierungs-Signale" data={calibrationSignals} />
          </div>
        </div>
      </div>
    </main>
  );
}
