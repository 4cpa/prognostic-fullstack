"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

type QuestionCreateResponse = {
  id: string;
  slug?: string | null;
};

type ForecastCreateResponse = {
  question?: { id?: string | null; slug?: string | null } | null;
  detail?: string | null;
};

type AppError =
  | { kind: "http"; status: number; detail: string }
  | { kind: "network"; msg: string };

const LANGUAGES = [
  { code: "de", flag: "🇩🇪", label: "DE" },
  { code: "en", flag: "🇬🇧", label: "EN" },
  { code: "it", flag: "🇮🇹", label: "IT" },
  { code: "fr", flag: "🇫🇷", label: "FR" },
  { code: "es", flag: "🇪🇸", label: "ES" },
] as const;

function resolveAtOneYear(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() + 1);
  return d.toISOString();
}

function logError(context: string, err: unknown) {
  const ts = new Date().toISOString();
  console.error(`[${ts}] [HomeForm] ${context}`, err);
}

export default function HomeForm() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [language, setLanguage] = useState<string>("de");
  const [error, setError] = useState<AppError | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;

    setError(null);
    setLoading(true);

    // 1. Frage anlegen
    let questionId: string;
    let questionSlug: string | null | undefined;
    try {
      const res = await fetch("/api/questions", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          title: q.length > 200 ? q.slice(0, 200) : q,
          description: q,
          resolve_at: resolveAtOneYear(),
          resolution_criteria: q,
        }),
      });

      const data = (await res.json()) as QuestionCreateResponse & { detail?: string };

      if (!res.ok) {
        const detail = data.detail ?? `HTTP ${res.status}`;
        logError(`POST /api/questions → ${res.status}`, detail);
        setError({ kind: "http", status: res.status, detail });
        setLoading(false);
        return;
      }

      if (!data.id) {
        logError("POST /api/questions → no id", data);
        setError({ kind: "http", status: 200, detail: "Frage angelegt, aber keine ID erhalten." });
        setLoading(false);
        return;
      }

      questionId = data.id;
      questionSlug = data.slug;
    } catch (err) {
      logError("POST /api/questions network error", err);
      setError({ kind: "network", msg: String(err) });
      setLoading(false);
      return;
    }

    // 2. Forecast erzeugen
    let forecastSlug: string | null | undefined;
    try {
      const res = await fetch(
        `/api/questions/${questionId}/forecast?method_version=v0.1.0&language=${language}`,
        { method: "POST", headers: { Accept: "application/json" } },
      );

      const data = (await res.json()) as ForecastCreateResponse & { detail?: string };

      if (!res.ok) {
        const detail = data.detail ?? `HTTP ${res.status}`;
        logError(`POST /api/questions/${questionId}/forecast → ${res.status}`, detail);
        setError({ kind: "http", status: res.status, detail });
        setLoading(false);
        return;
      }

      forecastSlug = data.question?.slug ?? data.question?.id ?? null;
    } catch (err) {
      logError(`POST /api/questions/${questionId}/forecast network error`, err);
      setError({ kind: "network", msg: String(err) });
      setLoading(false);
      return;
    }

    router.push(`/forecast/${forecastSlug ?? questionSlug ?? questionId}`);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (question.trim() && !loading) {
        handleSubmit(e as unknown as React.FormEvent);
      }
    }
  }

  return (
    <div className="w-full space-y-4">
      {/* Fehleranzeige */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <p className="font-medium">
            {error.kind === "http" && error.status === 404
              ? "Ressource nicht gefunden (404)"
              : error.kind === "http"
              ? `Serverfehler (${error.status})`
              : "Verbindungsfehler"}
          </p>
          <p className="mt-0.5 text-xs text-red-600">
            {error.kind === "network" ? error.msg : error.detail}
          </p>
        </div>
      )}

      {/* Eingabebereich */}
      <form onSubmit={handleSubmit} className="w-full">
        <div className="relative">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Deine Frage eingeben… z. B. «Wird es 2026 einen Weltkrieg geben?»"
            rows={3}
            required
            className="w-full resize-none rounded-2xl border border-slate-200 bg-white px-5 py-4 pr-14 text-base text-slate-900 shadow-sm outline-none placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-200"
          />
          <button
            type="submit"
            disabled={!question.trim() || loading}
            className="absolute bottom-3 right-3 flex h-9 w-9 items-center justify-center rounded-xl bg-slate-900 text-white transition hover:bg-slate-700 disabled:opacity-30"
            aria-label="Forecast erzeugen"
          >
            {loading ? (
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            ) : (
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            )}
          </button>
        </div>

        {/* Sprach-Auswahl */}
        <div className="mt-3 flex items-center gap-1.5">
          <span className="mr-1 text-xs text-slate-400">Sprache:</span>
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              type="button"
              onClick={() => setLanguage(lang.code)}
              className={`flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                language === lang.code
                  ? "bg-slate-900 text-white"
                  : "bg-slate-100 text-slate-500 hover:bg-slate-200 hover:text-slate-700"
              }`}
            >
              <span>{lang.flag}</span>
              <span>{lang.label}</span>
            </button>
          ))}
        </div>
      </form>
    </div>
  );
}
