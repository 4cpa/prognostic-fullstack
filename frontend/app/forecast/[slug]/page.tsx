import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";
export const revalidate = 0;

type RouteParams = { slug: string } | Promise<{ slug: string }>;
type PageProps = { params: RouteParams };

// ── Typen ───────────────────────────────────────────────────────────────────

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
};

type ClaimRecord = {
  id?: number | string;
  text?: string | null;
  claim_text?: string | null;
  source_title?: string | null;
  source_url?: string | null;
};

type ForecastRecord = {
  probability?: number | null;
  raw_probability?: number | null;
  calibrated_probability?: number | null;
  confidence?: number | null;
  explanation_md?: string | null;
  summary?: string | null;
  created_at?: string | null;
  direct_answer?: string | null;
  answer_label?: string | null;
  answer_confidence_band?: string | null;
  answer_rationale_short?: string | null;
  question_type?: string | null;
};

type ScenarioRecord = {
  title: string;
  description: string;
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
  raw_probability?: number | null;
  calibrated_probability?: number | null;
  direct_answer?: string | null;
  answer_label?: string | null;
  answer_confidence_band?: string | null;
  answer_rationale_short?: string | null;
  question_type?: string | null;
  scenarios?: ScenarioRecord[] | null;
  language?: string | null;
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
  const url = `${getApiBaseUrl()}${path}`;
  try {
    const res = await fetch(url, { cache: "no-store", headers: { Accept: "application/json" } });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return (await res.json()) as T;
  } catch (err) {
    console.error("apiFetch failed", { url, err });
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
  if (Array.isArray(payload) && payload.length > 0 && hasId(payload[0])) return payload[0];
  if (typeof payload !== "object") return null;
  const data = payload as Record<string, unknown>;
  if (hasId(data)) return data as QuestionRecord;
  if (Array.isArray(data.items) && hasId(data.items[0])) return data.items[0];
  if (Array.isArray(data.questions) && hasId(data.questions[0])) return data.questions[0];
  return null;
}

async function getQuestionBySlug(slug: string): Promise<QuestionRecord | null> {
  const enc = encodeURIComponent(slug);
  for (const path of [
    `/questions/slug/${enc}`,
    `/questions/by-slug/${enc}`,
    `/questions/${enc}`,
    `/questions?slug=${enc}`,
    `/questions?search=${enc}`,
  ]) {
    const q = normalizeQuestion(await apiFetch<unknown>(path));
    if (q?.id) return q;
  }
  return null;
}

async function getFullForecast(questionId: string): Promise<FullForecastResponse | null> {
  return apiFetch<FullForecastResponse>(`/questions/${questionId}/forecast/latest/full`);
}

// ── Hilfsfunktionen ─────────────────────────────────────────────────────────

function toPercent(v?: number | null): string {
  if (typeof v !== "number" || Number.isNaN(v)) return "—";
  const pct = v <= 1 ? v * 100 : v;
  return `${Math.round(pct * 10) / 10} %`;
}

function toPercentNum(v?: number | null): number | null {
  if (typeof v !== "number" || Number.isNaN(v)) return null;
  return Math.round((v <= 1 ? v * 100 : v) * 10) / 10;
}

function formatDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat("de-CH", { dateStyle: "medium" }).format(d);
}

function stripHtml(html: string): string {
  return html
    .replace(/<[^>]*>/g, " ")   // geschlossene Tags → Leerzeichen
    .replace(/<[^>]*/g, " ")    // ungeschlossene Tags (kein >) → Leerzeichen
    .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

function claimText(c: ClaimRecord): string {
  const raw = c.text || c.claim_text || "";
  if (!raw) return "";
  const cleaned = raw.includes("<") ? stripHtml(raw) : raw;
  return cleaned || "—";
}

// Minimal markdown → React nodes (server-side, no library needed)
function renderMarkdown(md: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const blocks = md.trim().split(/\n\n+/);

  blocks.forEach((block, bi) => {
    const lines = block.split("\n");

    // Heading
    if (/^#{1,3}\s/.test(lines[0])) {
      const text = lines[0].replace(/^#{1,3}\s+/, "");
      nodes.push(
        <h3 key={bi} className="mt-5 mb-2 text-base font-semibold text-slate-900">
          {inlineMarkdown(text)}
        </h3>
      );
      return;
    }

    // Bullet list
    if (lines.every((l) => /^[-*]\s/.test(l.trim()) || l.trim() === "")) {
      const items = lines.filter((l) => /^[-*]\s/.test(l.trim()));
      nodes.push(
        <ul key={bi} className="mb-3 space-y-1 pl-5 text-sm leading-6 text-slate-700 list-disc">
          {items.map((item, ii) => (
            <li key={ii}>{inlineMarkdown(item.replace(/^[-*]\s+/, ""))}</li>
          ))}
        </ul>
      );
      return;
    }

    // Paragraph
    const text = lines.join(" ").trim();
    if (text) {
      nodes.push(
        <p key={bi} className="mb-3 text-sm leading-7 text-slate-800">
          {inlineMarkdown(text)}
        </p>
      );
    }
  });

  return nodes;
}

function inlineMarkdown(text: string): React.ReactNode {
  // Handle **bold**
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  if (parts.length === 1) return text;
  return (
    <>
      {parts.map((part, i) =>
        /^\*\*[^*]+\*\*$/.test(part) ? (
          <strong key={i}>{part.slice(2, -2)}</strong>
        ) : (
          part
        )
      )}
    </>
  );
}

// Tone helpers
function answerTone(label?: string | null): "yes" | "lean_yes" | "uncertain" | "lean_no" | "no" | "analytical" {
  switch (label) {
    case "yes":        return "yes";
    case "lean_yes":   return "lean_yes";
    case "no":         return "no";
    case "lean_no":    return "lean_no";
    case "analytical": return "analytical";
    default:           return "uncertain";
  }
}

type Tone = ReturnType<typeof answerTone>;

const TONE_CARD: Record<Tone, string> = {
  yes:        "border-green-200 bg-green-50",
  lean_yes:   "border-green-200 bg-green-50",
  no:         "border-red-200 bg-red-50",
  lean_no:    "border-red-200 bg-red-50",
  uncertain:  "border-amber-200 bg-amber-50",
  analytical: "border-blue-200 bg-blue-50",
};

const TONE_BADGE: Record<Tone, string> = {
  yes:        "bg-green-100 text-green-900 border-green-300",
  lean_yes:   "bg-green-100 text-green-900 border-green-300",
  no:         "bg-red-100 text-red-900 border-red-300",
  lean_no:    "bg-red-100 text-red-900 border-red-300",
  uncertain:  "bg-amber-100 text-amber-900 border-amber-300",
  analytical: "bg-blue-100 text-blue-900 border-blue-300",
};

const LABEL_TEXT: Record<string, string> = {
  yes:        "Ja",
  lean_yes:   "Eher Ja",
  no:         "Nein",
  lean_no:    "Eher Nein",
  uncertain:  "Unklar",
  analytical: "Analytische Einschätzung",
};

const BAND_TEXT: Record<string, string> = {
  likely:     "Wahrscheinlich",
  moderate:   "Moderat",
  close_call: "Knapp",
  unlikely:   "Unwahrscheinlich",
  analytical: "Analytisch",
};

// ── Übersetzungen ───────────────────────────────────────────────────────────

type Lang = "de" | "en" | "fr" | "it" | "es";

const T: Record<Lang, {
  analysis: string;
  signals: string;
  pro: string;
  contra: string;
  uncertainty: string;
  sources: string;
  probability: string;
  scenarios: string;
  noScenarios: string;
  noPro: string;
  noContra: string;
  noUncertainty: string;
  noSources: string;
  createdAt: string;
}> = {
  de: {
    analysis: "Analyse",
    signals: "Signale & Argumente",
    pro: "Pro",
    contra: "Contra",
    uncertainty: "Unsicherheiten",
    sources: "Quellen",
    probability: "Wahrscheinlichkeit",
    scenarios: "Mögliche Szenarien",
    noScenarios: "Keine Szenarien verfügbar.",
    noPro: "Keine Pro-Signale",
    noContra: "Keine Contra-Signale",
    noUncertainty: "Keine Unsicherheiten",
    noSources: "Keine Quellen vorhanden.",
    createdAt: "Forecast vom",
  },
  en: {
    analysis: "Analysis",
    signals: "Signals & Arguments",
    pro: "Pro",
    contra: "Contra",
    uncertainty: "Uncertainties",
    sources: "Sources",
    probability: "Probability",
    scenarios: "Possible Scenarios",
    noScenarios: "No scenarios available.",
    noPro: "No pro signals",
    noContra: "No contra signals",
    noUncertainty: "No uncertainties",
    noSources: "No sources available.",
    createdAt: "Forecast from",
  },
  fr: {
    analysis: "Analyse",
    signals: "Signaux & Arguments",
    pro: "Pour",
    contra: "Contre",
    uncertainty: "Incertitudes",
    sources: "Sources",
    probability: "Probabilité",
    scenarios: "Scénarios possibles",
    noScenarios: "Aucun scénario disponible.",
    noPro: "Aucun signal positif",
    noContra: "Aucun signal négatif",
    noUncertainty: "Aucune incertitude",
    noSources: "Aucune source disponible.",
    createdAt: "Prévision du",
  },
  it: {
    analysis: "Analisi",
    signals: "Segnali & Argomenti",
    pro: "Pro",
    contra: "Contro",
    uncertainty: "Incertezze",
    sources: "Fonti",
    probability: "Probabilità",
    scenarios: "Scenari possibili",
    noScenarios: "Nessuno scenario disponibile.",
    noPro: "Nessun segnale positivo",
    noContra: "Nessun segnale negativo",
    noUncertainty: "Nessuna incertezza",
    noSources: "Nessuna fonte disponibile.",
    createdAt: "Previsione del",
  },
  es: {
    analysis: "Análisis",
    signals: "Señales & Argumentos",
    pro: "A favor",
    contra: "En contra",
    uncertainty: "Incertidumbres",
    sources: "Fuentes",
    probability: "Probabilidad",
    scenarios: "Posibles escenarios",
    noScenarios: "No hay escenarios disponibles.",
    noPro: "Sin señales a favor",
    noContra: "Sin señales en contra",
    noUncertainty: "Sin incertidumbres",
    noSources: "No hay fuentes disponibles.",
    createdAt: "Pronóstico del",
  },
};

function t(lang: string | null | undefined): typeof T["de"] {
  const l = (lang ?? "de").toLowerCase().slice(0, 2) as Lang;
  return T[l] ?? T["de"];
}

// ── Seite ───────────────────────────────────────────────────────────────────

export default async function ForecastDetailPage({ params }: PageProps) {
  const { slug } = await Promise.resolve(params);
  if (!slug) notFound();

  const question = await getQuestionBySlug(slug);
  if (!question?.id) notFound();

  const full = await getFullForecast(question.id);
  if (!full) notFound();

  const forecast = full.forecast ?? {};
  const questionData = full.question ?? question;

  const questionText = questionData.title || questionData.question || "Forecast";

  const directAnswer  = full.direct_answer  ?? forecast.direct_answer  ?? null;
  const answerLabel   = full.answer_label   ?? forecast.answer_label   ?? null;
  const answerBand    = full.answer_confidence_band ?? forecast.answer_confidence_band ?? null;
  const answerRationale = full.answer_rationale_short ?? forecast.answer_rationale_short ?? null;
  const questionType  = full.question_type ?? null;
  const scenarios     = (full.scenarios ?? []).filter((s) => s.title);
  const language      = full.language ?? "de";
  const tr            = t(language);

  // Detect open question: from stored type, answer label, or question text as fallback
  const OPEN_PREFIXES = /^(was|wer|wann|wo|wie|warum|welche[rs]?|wieviel|wie\s+viel|womit|wozu|wohin|wof[üu]r|wor[üu]ber|inwiefern|inwieweit)\b/i;
  const isOpenQuestion =
    questionType === "open" ||
    answerLabel === "analytical" ||
    OPEN_PREFIXES.test(questionText.trim());

  const probability = full.calibrated_probability ?? full.raw_probability ?? forecast.probability;
  const pctNum = toPercentNum(probability);

  const tone = answerTone(answerLabel);

  const explanationMd = forecast.explanation_md || full.summary || forecast.summary || "";
  const proClaims     = full.top_pro_claims    ?? [];
  const contraClaims  = full.top_contra_claims ?? [];
  const uncertainties = full.top_uncertainties ?? [];
  const sources       = full.sources           ?? [];

  // Probability bar fill (0–100)
  const barFill = pctNum !== null ? Math.min(100, Math.max(0, pctNum)) : 0;
  const barColor =
    barFill >= 65 ? "bg-green-500" :
    barFill >= 40 ? "bg-amber-400" :
    "bg-red-400";

  return (
    <main id="main-content" className="min-h-screen bg-slate-50 overflow-x-hidden">
      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">

        {/* ── Frage ── */}
        <h1 className="mb-6 text-2xl font-bold leading-snug tracking-tight text-slate-950 sm:text-3xl break-words">
          {questionText}
        </h1>

        {/* ── Offene Frage: Szenarien ── */}
        {isOpenQuestion ? (
          <div className="mb-6 space-y-3">
            {/* Einleitungstext */}
            {directAnswer && (
              <p className="text-base leading-7 text-slate-700 break-words">{directAnswer}</p>
            )}

            {/* Szenario-Karten */}
            {scenarios.length > 0 ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {scenarios.map((s, i) => (
                  <div
                    key={i}
                    className="rounded-2xl border border-blue-200 bg-blue-50 p-5"
                  >
                    <p className="text-sm font-semibold text-blue-900 mb-1 break-words">
                      {s.title}
                    </p>
                    <p className="text-sm leading-6 text-slate-700 break-words">{s.description}</p>
                  </div>
                ))}
              </div>
            ) : directAnswer ? null : (
              <p className="text-sm text-slate-500">{tr.noScenarios}</p>
            )}

            {/* Kurzbegründung */}
            {answerRationale && (
              <p className="text-xs text-slate-500 pt-1">{answerRationale}</p>
            )}
          </div>
        ) : (
          <>
            {/* ── Geschlossene Frage: Einschätzung ── */}
            <div className={`mb-6 rounded-2xl border-2 p-6 ${TONE_CARD[tone]}`}>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                {answerLabel && (
                  <span className={`inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${TONE_BADGE[tone]}`}>
                    {LABEL_TEXT[answerLabel] ?? answerLabel}
                  </span>
                )}
                {answerBand && (
                  <span className="inline-flex rounded-full border border-slate-300 bg-white/70 px-3 py-1 text-xs text-slate-600">
                    {BAND_TEXT[answerBand] ?? answerBand}
                  </span>
                )}
              </div>

              <p className="text-lg font-semibold leading-7 text-slate-950 break-words">
                {directAnswer || "Gemini-Antwort wird berechnet…"}
              </p>

              {answerRationale && (
                <p className="mt-3 text-sm leading-6 text-slate-700 border-t border-black/10 pt-3">
                  {answerRationale}
                </p>
              )}
            </div>

            {/* ── Wahrscheinlichkeit ── */}
            {pctNum !== null && (
              <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-5">
                <div className="flex items-baseline justify-between mb-2">
                  <span className="text-sm font-semibold text-slate-600 uppercase tracking-wide">
                    {tr.probability}
                  </span>
                  <span className="text-2xl font-bold text-slate-950">
                    {toPercent(probability)}
                  </span>
                </div>
                <div className="h-2.5 w-full rounded-full bg-slate-200 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${barColor}`}
                    style={{ width: `${barFill}%` }}
                    role="progressbar"
                    aria-valuenow={barFill}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`Wahrscheinlichkeit: ${pctNum} Prozent`}
                  />
                </div>
                <div className="mt-1.5 flex justify-between text-xs text-slate-400">
                  <span>0 %</span>
                  <span>100 %</span>
                </div>
              </div>
            )}
          </>
        )}

        {/* ── Gemini-Analyse ── */}
        {explanationMd && (
          <section
            aria-labelledby="section-analyse"
            className="mb-6 rounded-2xl border border-slate-200 bg-white p-6"
          >
            <h2 id="section-analyse" className="mb-4 text-lg font-semibold text-slate-900">
              {tr.analysis}
            </h2>
            <div>{renderMarkdown(explanationMd)}</div>
          </section>
        )}

        {/* ── Signale ── */}
        {(proClaims.length > 0 || contraClaims.length > 0 || uncertainties.length > 0) && (
          <section
            aria-labelledby="section-signale"
            className="mb-6 rounded-2xl border border-slate-200 bg-white p-6"
          >
            <h2 id="section-signale" className="mb-5 text-lg font-semibold text-slate-900">
              {tr.signals}
            </h2>

            <div className="grid gap-5 sm:grid-cols-3">
              {/* Pro */}
              <div>
                <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-green-700">
                  <span aria-hidden="true">↑</span> {tr.pro}
                </h3>
                {proClaims.length === 0 ? (
                  <p className="text-xs text-slate-500">{tr.noPro}</p>
                ) : (
                  <ul className="space-y-3">
                    {proClaims.map((c, i) => (
                      <li key={String(c.id ?? i)} className="text-sm leading-5 text-slate-800">
                        <p className="break-all">{claimText(c)}</p>
                        {(c.source_url || c.source_title) && (
                          <p className="mt-1 text-xs text-slate-400">
                            {c.source_url ? (
                              <a
                                href={c.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="underline hover:text-slate-600"
                              >
                                {c.source_title || c.source_url}
                                <span className="sr-only"> (öffnet in neuem Tab)</span>
                              </a>
                            ) : c.source_title}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Contra */}
              <div>
                <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-red-700">
                  <span aria-hidden="true">↓</span> {tr.contra}
                </h3>
                {contraClaims.length === 0 ? (
                  <p className="text-xs text-slate-500">{tr.noContra}</p>
                ) : (
                  <ul className="space-y-3">
                    {contraClaims.map((c, i) => (
                      <li key={String(c.id ?? i)} className="text-sm leading-5 text-slate-800">
                        <p className="break-all">{claimText(c)}</p>
                        {(c.source_url || c.source_title) && (
                          <p className="mt-1 text-xs text-slate-400">
                            {c.source_url ? (
                              <a
                                href={c.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="underline hover:text-slate-600"
                              >
                                {c.source_title || c.source_url}
                                <span className="sr-only"> (öffnet in neuem Tab)</span>
                              </a>
                            ) : c.source_title}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Unsicherheiten */}
              <div>
                <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-amber-700">
                  <span aria-hidden="true">~</span> {tr.uncertainty}
                </h3>
                {uncertainties.length === 0 ? (
                  <p className="text-xs text-slate-500">{tr.noUncertainty}</p>
                ) : (
                  <ul className="space-y-3">
                    {uncertainties.map((c, i) => (
                      <li key={String(c.id ?? i)} className="text-sm leading-5 text-slate-800">
                        <p className="break-all">{claimText(c)}</p>
                        {(c.source_url || c.source_title) && (
                          <p className="mt-1 text-xs text-slate-400">
                            {c.source_url ? (
                              <a
                                href={c.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="underline hover:text-slate-600"
                              >
                                {c.source_title || c.source_url}
                                <span className="sr-only"> (öffnet in neuem Tab)</span>
                              </a>
                            ) : c.source_title}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </section>
        )}

        {/* ── Quellen ── */}
        {sources.length > 0 && (
          <section
            aria-labelledby="section-quellen"
            className="mb-6 rounded-2xl border border-slate-200 bg-white p-6"
          >
            <h2 id="section-quellen" className="mb-4 text-lg font-semibold text-slate-900">
              {tr.sources} ({sources.length})
            </h2>

            <ul className="divide-y divide-slate-100">
              {sources.map((s, i) => (
                <li key={String(s.id ?? i)} className="py-4 first:pt-0 last:pb-0">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <h3 className="text-sm font-semibold text-slate-900 leading-5 break-words">
                        {s.url ? (
                          <a
                            href={s.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:underline text-slate-900 break-all"
                          >
                            {s.title || s.url}
                            <span className="sr-only"> (öffnet in neuem Tab)</span>
                          </a>
                        ) : (
                          s.title || "Ohne Titel"
                        )}
                      </h3>
                      {(s.summary || s.excerpt) && (
                        <p className="mt-1 text-xs leading-5 text-slate-600 line-clamp-3 break-all">
                          {stripHtml(s.summary || s.excerpt || "")}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-1 shrink-0">
                      {s.domain && (
                        <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                          {s.domain}
                        </span>
                      )}
                      {s.published_at && (
                        <span className="text-xs text-slate-400">{formatDate(s.published_at)}</span>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* ── Metadaten (diskret) ── */}
        <p className="text-xs text-slate-400 text-center">
          {tr.createdAt} {formatDate(forecast.created_at)} · {questionData.slug ?? questionData.id}
        </p>

      </div>
    </main>
  );
}
