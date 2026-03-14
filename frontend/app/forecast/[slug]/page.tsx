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
  probability: number;
  confidence?: number | null;
  method: string;
  method_version: string;
  explanation_md: string;
  inputs_hash: string;
};

type ForecastQuestion = {
  id?: string | null;
  title?: string | null;
  category?: string | null;
  resolve_at?: string | null;
  resolution_criteria?: string | null;
  resolution_source_policy?: string | null;
};

type ForecastSource = {
  id: string;
  forecast_id: string;
  url: string;
  title: string;
  publisher: string;
  domain?: string | null;
  source_type: string;
  published_at?: string | null;
  query?: string | null;
  retrieval_method?: string | null;
  relevance_score: number;
  credibility_score: number;
  freshness_score: number;
  overall_score: number;
  stance: string;
  signal_strength: number;
  summary?: string | null;
  created_at?: string | null;
};

type ForecastClaim = {
  id: string;
  forecast_id: string;
  claim_text: string;
  claim_type: string;
  source_url: string;
  source_title: string;
  source_type: string;
  claim_confidence: number;
  time_relevance: number;
  source_quality_weight?: number | null;
  claim_confidence_weight?: number | null;
  time_relevance_weight?: number | null;
  relevance_weight?: number | null;
  freshness_weight?: number | null;
  independence_weight?: number | null;
  specificity_weight?: number | null;
  support_boost?: number | null;
  final_weight?: number | null;
  direction?: number | null;
  signed_weight?: number | null;
  supporting_source_count?: number | null;
  supporting_domain_count?: number | null;
  created_at?: string | null;
};

type RuntimeCalibrationMeta = {
  record_count?: number;
  num_bins?: number;
  min_bin_count?: number;
  overall_brier_score?: number;
  overall_mae?: number;
  overall_rmse?: number;
};

type ForecastDiagnostics = {
  source_count: number;
  claim_count: number;
  source_counts: Record<string, number>;
  claim_counts: Record<string, number>;
  pro_weight_sum: number;
  contra_weight_sum: number;
  uncertainty_weight_sum: number;
  background_weight_sum: number;
  net_signal: number;
  raw_probability?: number;
  calibrated_probability?: number;
  runtime_calibration_meta?: RuntimeCalibrationMeta;
};

type FullForecastResponse = {
  question: ForecastQuestion;
  forecast: ForecastRead & {
    raw_probability?: number;
    calibrated_probability?: number;
    calibration_signals?: string[];
    runtime_calibration_meta?: RuntimeCalibrationMeta;
    calibration?: Record<string, unknown>;
  };
  summary: string;
  sources: ForecastSource[];
  claims: ForecastClaim[];
  source_counts: Record<string, number>;
  claim_counts: Record<string, number>;
  diagnostics: ForecastDiagnostics;
  top_pro_claims: ForecastClaim[];
  top_contra_claims: ForecastClaim[];
  top_uncertainties: ForecastClaim[];
  top_background: ForecastClaim[];
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

function toPercentFromNormalized(probability?: number | null): string {
  if (probability == null || Number.isNaN(probability)) return "n/a";
  const normalized = Math.min(Math.max(probability, 0), 1);
  return `${(normalized * 100).toFixed(1)}%`;
}

function toPercentAuto(probability?: number | null): string {
  if (probability == null || Number.isNaN(probability)) return "n/a";
  const normalized =
    probability > 1 ? Math.min(Math.max(probability / 100, 0), 1) : Math.min(Math.max(probability, 0), 1);
  return `${(normalized * 100).toFixed(1)}%`;
}

function formatConfidence(confidence?: number | null): string | null {
  if (confidence == null || Number.isNaN(confidence)) return null;
  const normalized = Math.min(Math.max(confidence, 0), 100);
  return `${normalized.toFixed(1)}%`;
}

function formatDate(value?: string | null): string {
  if (!value) return "n/a";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString("de-DE", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

function scoreLabel(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return "n/a";
  return value.toFixed(4);
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

async function getLatestForecastFull(questionId: string): Promise<FullForecastResponse> {
  const base = apiBase();

  const res = await fetch(`${base}/questions/${questionId}/forecast/latest/full`, {
    method: "GET",
    cache: "no-store",
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Fehler beim Laden der vollständigen Prognose (${res.status}): ${txt}`);
  }

  return res.json();
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-8 rounded-xl bg-white p-6 shadow-md">
      <h2 className="mb-4 text-xl font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function MetricCard({
  label,
  value,
  subtext,
}: {
  label: string;
  value: string;
  subtext?: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 p-4">
      <p className="mb-1 text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
      {subtext ? <p className="mt-1 text-xs text-gray-500">{subtext}</p> : null}
    </div>
  );
}

function ClaimList({
  claims,
  emptyText,
}: {
  claims: ForecastClaim[];
  emptyText: string;
}) {
  if (!claims.length) {
    return <p className="text-gray-600">{emptyText}</p>;
  }

  return (
    <div className="space-y-3">
      {claims.map((claim) => (
        <div key={claim.id} className="rounded-lg border border-gray-200 p-4">
          <p className="mb-2 text-sm leading-6 text-gray-900">{claim.claim_text}</p>
          <div className="text-xs text-gray-600">
            <span className="mr-3">Quelle: {claim.source_title || "n/a"}</span>
            <span className="mr-3">Typ: {claim.source_type || "n/a"}</span>
            <span className="mr-3">Gewicht: {scoreLabel(claim.final_weight)}</span>
            <span>Confidence: {scoreLabel(claim.claim_confidence)}</span>
          </div>
        </div>
      ))}
    </div>
  );
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
  await createForecast(q.id);
  const full = await getLatestForecastFull(q.id);

  const forecast = full.forecast;
  const question = full.question;
  const rawProbability = forecast.raw_probability;
  const calibratedProbability = forecast.calibrated_probability;
  const calibrationMeta = forecast.runtime_calibration_meta || full.diagnostics.runtime_calibration_meta || {};

  return (
    <div className="min-h-screen bg-gray-50 p-10">
      <h1 className="mb-2 text-3xl font-bold">Prognose</h1>
      <p className="mb-2 text-gray-600">
        Slug: <span className="font-mono">{slug}</span> — Question ID:{" "}
        <span className="font-mono">{q.id}</span>
      </p>
      <p className="mb-8 text-gray-600">
        Titel: <span className="font-medium">{question.title || humanizeSlug(slug)}</span>
      </p>

      <Section title="Ergebnis">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Eintrittswahrscheinlichkeit"
            value={toPercentAuto(forecast.probability)}
            subtext="Persistierter Forecast-Wert"
          />
          <MetricCard
            label="Rohwahrscheinlichkeit"
            value={toPercentFromNormalized(rawProbability)}
            subtext="Vor Kalibrierung"
          />
          <MetricCard
            label="Kalibrierte Wahrscheinlichkeit"
            value={toPercentFromNormalized(calibratedProbability)}
            subtext="Nach Backtesting/Kalibrierung"
          />
          <MetricCard
            label="Confidence"
            value={formatConfidence(forecast.confidence) ?? "n/a"}
            subtext="Heuristische Modell-Sicherheit"
          />
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-gray-200 p-4 text-sm text-gray-700">
            <p className="mb-2 font-medium">Forecast-Metadaten</p>
            <p>Methode: {forecast.method}</p>
            <p>Version: {forecast.method_version}</p>
            <p>Auflösung: {formatDate(question.resolve_at)}</p>
            <p>Kategorie: {question.category || "n/a"}</p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 text-sm text-gray-700">
            <p className="mb-2 font-medium">Kalibrierungs-Meta</p>
            <p>Backtest-Records: {calibrationMeta.record_count ?? 0}</p>
            <p>Buckets: {calibrationMeta.num_bins ?? "n/a"}</p>
            <p>Min Bin Count: {calibrationMeta.min_bin_count ?? "n/a"}</p>
            <p>Brier Score: {scoreLabel(calibrationMeta.overall_brier_score)}</p>
            <p>MAE: {scoreLabel(calibrationMeta.overall_mae)}</p>
            <p>RMSE: {scoreLabel(calibrationMeta.overall_rmse)}</p>
          </div>
        </div>

        {forecast.calibration_signals?.length ? (
          <div className="mt-4 rounded-lg border border-gray-200 p-4 text-sm text-gray-700">
            <p className="mb-2 font-medium">Kalibrierungs-Signale</p>
            <ul className="list-disc space-y-1 pl-5">
              {forecast.calibration_signals.map((signal, index) => (
                <li key={`${signal}-${index}`}>{signal}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </Section>

      <Section title="Kurzbegründung">
        <p className="leading-7 text-gray-800">
          {full.summary || "Noch keine strukturierte Kurzbegründung verfügbar."}
        </p>
      </Section>

      <Section title="Gründe, die für das Eintreten sprechen">
        <ClaimList
          claims={full.top_pro_claims}
          emptyText="Keine stark gewichteten Pro-Claims vorhanden."
        />
      </Section>

      <Section title="Gründe, die gegen das Eintreten sprechen">
        <ClaimList
          claims={full.top_contra_claims}
          emptyText="Keine stark gewichteten Contra-Claims vorhanden."
        />
      </Section>

      <Section title="Unsicherheiten">
        <ClaimList
          claims={full.top_uncertainties}
          emptyText="Keine stark gewichteten Unsicherheits-Claims vorhanden."
        />
      </Section>

      <Section title="Diagnostik">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div className="rounded-lg border border-gray-200 p-4 text-sm text-gray-700">
            <p className="mb-2 font-medium">Quellen</p>
            <p>Gesamt: {full.diagnostics.source_count}</p>
            <p>Official: {full.source_counts.official ?? 0}</p>
            <p>Wire: {full.source_counts.wire ?? 0}</p>
            <p>Research: {full.source_counts.research ?? 0}</p>
            <p>Major Media: {full.source_counts.major_media ?? 0}</p>
            <p>Other: {full.source_counts.other ?? 0}</p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 text-sm text-gray-700">
            <p className="mb-2 font-medium">Claims</p>
            <p>Gesamt: {full.diagnostics.claim_count}</p>
            <p>Pro: {full.claim_counts.pro ?? 0}</p>
            <p>Contra: {full.claim_counts.contra ?? 0}</p>
            <p>Uncertainty: {full.claim_counts.uncertainty ?? 0}</p>
            <p>Background: {full.claim_counts.background ?? 0}</p>
            <p>Net Signal: {scoreLabel(full.diagnostics.net_signal)}</p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 text-sm text-gray-700">
            <p className="mb-2 font-medium">Probability / Calibration</p>
            <p>Persistiert: {toPercentAuto(forecast.probability)}</p>
            <p>Roh: {toPercentFromNormalized(full.diagnostics.raw_probability)}</p>
            <p>Kalibriert: {toPercentFromNormalized(full.diagnostics.calibrated_probability)}</p>
            <p>Brier Score: {scoreLabel(calibrationMeta.overall_brier_score)}</p>
          </div>
        </div>
      </Section>

      <Section title="Quellen">
        {!full.sources.length ? (
          <p className="text-gray-600">Keine Quellen verfügbar.</p>
        ) : (
          <div className="space-y-4">
            {full.sources.map((source) => (
              <div key={source.id} className="rounded-lg border border-gray-200 p-4">
                <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-gray-600">
                  <span className="rounded bg-gray-100 px-2 py-1">{source.source_type}</span>
                  <span className="rounded bg-gray-100 px-2 py-1">{source.stance}</span>
                  <span className="rounded bg-gray-100 px-2 py-1">
                    Score {scoreLabel(source.overall_score)}
                  </span>
                  <span className="rounded bg-gray-100 px-2 py-1">
                    {source.publisher || source.domain || "unknown"}
                  </span>
                  <span className="rounded bg-gray-100 px-2 py-1">
                    {formatDate(source.published_at)}
                  </span>
                </div>

                <h3 className="mb-2 text-base font-semibold text-gray-900">{source.title}</h3>

                {source.url ? (
                  <p className="mb-2 break-all text-sm">
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-700 underline"
                    >
                      {source.url}
                    </a>
                  </p>
                ) : null}

                {source.summary ? (
                  <p className="text-sm leading-6 text-gray-700">{source.summary}</p>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Roh-Erklärung">
        <div className="prose max-w-none">
          <pre className="whitespace-pre-wrap">{forecast.explanation_md}</pre>
        </div>
      </Section>
    </div>
  );
}
