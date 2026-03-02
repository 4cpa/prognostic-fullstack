"use client";

import React, { useMemo, useState } from "react";
import {
  createForecast,
  createQuestion,
  getForecasts,
  type ForecastRead,
  type QuestionCreate,
  type QuestionRead,
} from "../lib/api";

function isoFromDateOnly(dateStr: string): string {
  // dateStr: YYYY-MM-DD
  // Wir setzen 12:00 UTC, damit es keine TZ-Überraschungen gibt.
  return new Date(`${dateStr}T12:00:00.000Z`).toISOString();
}

function defaultResolveDatePlusDays(days: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + days);
  const yyyy = d.getUTCFullYear();
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(d.getUTCDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`; // YYYY-MM-DD
}

function toPercent(p: number): string {
  if (!Number.isFinite(p)) return "–";
  const pct = Math.round(p * 1000) / 10; // 1 Nachkommastelle
  return `${pct.toFixed(1)}%`;
}

function stripMarkdown(md: string): string {
  // simpel & robust genug: entfernt die häufigsten Markdown-Syntaxteile
  return md
    .replace(/```[\s\S]*?```/g, "") // code blocks
    .replace(/`([^`]+)`/g, "$1") // inline code
    .replace(/!\[.*?\]\(.*?\)/g, "") // images
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // links
    .replace(/[#>*_~\-]{1,}/g, " ") // markdown chars
    .replace(/\s+/g, " ")
    .trim();
}

function germanForecastText(opts: {
  qTitle: string;
  qDescription: string;
  resolveAtIso: string;
  resolutionCriteria: string;
  sourcePolicy: string;
  probability: number;
  explanationMd: string;
}): string {
  const resolveAt = new Date(opts.resolveAtIso);
  const resolveAtDe = Number.isNaN(resolveAt.getTime())
    ? opts.resolveAtIso
    : resolveAt.toLocaleDateString("de-CH", {
        year: "numeric",
        month: "long",
        day: "2-digit",
      });

  const explanation = stripMarkdown(opts.explanationMd);
  const pct = toPercent(opts.probability);

  return [
    `Prognose: Für die Frage „${opts.qTitle}“ liegt die geschätzte Eintrittswahrscheinlichkeit bei ${pct}.`,
    `Kontext: ${opts.qDescription}`,
    `Auflösung: Die Frage wird voraussichtlich am ${resolveAtDe} entschieden.`,
    `Kriterien: ${opts.resolutionCriteria}`,
    `Quellenregel: ${opts.sourcePolicy}`,
    explanation ? `Begründung: ${explanation}` : "",
  ]
    .filter(Boolean)
    .join(" ");
}

export default function Page() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [resolutionCriteria, setResolutionCriteria] = useState(
    "Resolve based on the stated question outcome. Use official sources and at least one major wire service if applicable."
  );
  const [resolveDate, setResolveDate] = useState(defaultResolveDatePlusDays(180)); // default: +180 Tage
  const [category, setCategory] = useState("politics");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [createdQuestion, setCreatedQuestion] = useState<QuestionRead | null>(null);
  const [createdForecast, setCreatedForecast] = useState<ForecastRead | null>(null);
  const [forecasts, setForecasts] = useState<ForecastRead[] | null>(null);

  const canSubmit = useMemo(() => {
    return (
      !loading &&
      title.trim().length > 0 &&
      description.trim().length > 0 &&
      resolutionCriteria.trim().length > 0 &&
      resolveDate.trim().length === 10
    );
  }, [loading, title, description, resolutionCriteria, resolveDate]);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault(); // iPhone/Safari: verhindert Reload auf "/"
    if (!canSubmit) return;

    setError(null);
    setCreatedQuestion(null);
    setCreatedForecast(null);
    setForecasts(null);

    setLoading(true);
    try {
      const payload: QuestionCreate = {
        title: title.trim(),
        description: description.trim(),
        category: category.trim() || "politics",
        resolve_at: isoFromDateOnly(resolveDate),
        resolution_criteria: resolutionCriteria.trim(),
      };

      // 1) Question erstellen
      const q = await createQuestion(payload);
      setCreatedQuestion(q);

      // 2) Forecast erstellen
      const f = await createForecast(q.id, "v0.1.0");
      setCreatedForecast(f);

      // 3) Forecasts laden (Liste)
      const list = await getForecasts(q.id);
      setForecasts(list);
    } catch (err: any) {
      setError(err?.message ?? "Unbekannter Fehler");
    } finally {
      setLoading(false);
    }
  }

  const germanText =
    createdQuestion && createdForecast
      ? germanForecastText({
          qTitle: createdQuestion.title,
          qDescription: createdQuestion.description,
          resolveAtIso: createdQuestion.resolve_at,
          resolutionCriteria: createdQuestion.resolution_criteria,
          sourcePolicy: createdQuestion.resolution_source_policy,
          probability: createdForecast.probability,
          explanationMd: createdForecast.explanation_md,
        })
      : null;

  return (
    <main style={{ padding: 24, maxWidth: 980, margin: "0 auto" }}>
      <h1 style={{ fontSize: 28, fontWeight: 700 }}>4CPA Prognose</h1>

      <form onSubmit={onSubmit} style={{ marginTop: 16, display: "grid", gap: 12 }}>
        <label style={{ display: "grid", gap: 6 }}>
          <span style={{ fontSize: 14, opacity: 0.85 }}>Titel</span>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="z.B. Wird die EU bis Ende 2026 zerbrechen?"
            style={{ padding: 12, fontSize: 16, border: "1px solid #ddd", borderRadius: 8 }}
            autoComplete="off"
            enterKeyHint="go"
          />
        </label>

        <label style={{ display: "grid", gap: 6 }}>
          <span style={{ fontSize: 14, opacity: 0.85 }}>Beschreibung</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Kontext / genauer Wortlaut / Bedingungen…"
            rows={4}
            style={{ padding: 12, fontSize: 16, border: "1px solid #ddd", borderRadius: 8 }}
          />
        </label>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <label style={{ display: "grid", gap: 6 }}>
            <span style={{ fontSize: 14, opacity: 0.85 }}>Resolve Date</span>
            <input
              type="date"
              value={resolveDate}
              onChange={(e) => setResolveDate(e.target.value)}
              style={{ padding: 12, fontSize: 16, border: "1px solid #ddd", borderRadius: 8 }}
            />
          </label>

          <label style={{ display: "grid", gap: 6 }}>
            <span style={{ fontSize: 14, opacity: 0.85 }}>Kategorie</span>
            <input
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="politics"
              style={{ padding: 12, fontSize: 16, border: "1px solid #ddd", borderRadius: 8 }}
              autoComplete="off"
            />
          </label>
        </div>

        <label style={{ display: "grid", gap: 6 }}>
          <span style={{ fontSize: 14, opacity: 0.85 }}>Resolution Criteria</span>
          <textarea
            value={resolutionCriteria}
            onChange={(e) => setResolutionCriteria(e.target.value)}
            rows={3}
            style={{ padding: 12, fontSize: 16, border: "1px solid #ddd", borderRadius: 8 }}
          />
        </label>

        <button
          type="submit"
          disabled={!canSubmit}
          style={{
            padding: 12,
            fontSize: 16,
            borderRadius: 8,
            border: "1px solid #ddd",
            cursor: canSubmit ? "pointer" : "not-allowed",
          }}
        >
          {loading ? "Berechne…" : "Prognose anzeigen"}
        </button>

        {error && (
          <p style={{ margin: 0, color: "crimson" }}>
            Fehler: {error}
          </p>
        )}
      </form>

      {germanText && (
        <section style={{ marginTop: 24 }}>
          <h2 style={{ fontSize: 20, fontWeight: 600 }}>Antwort</h2>
          <div style={{ padding: 12, border: "1px solid #ddd", borderRadius: 8, lineHeight: 1.6 }}>
            {germanText}
          </div>
        </section>
      )}

      {/* optional: Debug-Info behalten */}
      {forecasts && forecasts.length > 0 && (
        <section style={{ marginTop: 16 }}>
          <div style={{ fontSize: 14, opacity: 0.8 }}>
            Forecasts vorhanden: {forecasts.length}
          </div>
        </section>
      )}
    </main>
  );
}
