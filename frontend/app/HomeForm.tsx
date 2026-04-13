"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { getStoredApiKey } from "./ApiKeyBanner";

type QuestionCreateResponse = {
  id: string;
  slug?: string | null;
};

type ForecastCreateResponse = {
  question?: { id?: string | null; slug?: string | null } | null;
  detail?: string | null;
};

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

export default function HomeForm() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [language, setLanguage] = useState<string>("de");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;

    setError(null);
    setLoading(true);

    const apiKey = getStoredApiKey();
    const authHeaders: Record<string, string> = apiKey
      ? { "X-Anthropic-Key": apiKey }
      : {};

    // 1. Frage anlegen — fehlende Felder automatisch befüllen
    let questionId: string;
    let questionSlug: string | null | undefined;
    try {
      const res = await fetch("/api/questions", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json", ...authHeaders },
        body: JSON.stringify({
          title: q.length > 200 ? q.slice(0, 200) : q,
          description: q,
          resolve_at: resolveAtOneYear(),
          resolution_criteria: q,
        }),
      });
      const data = (await res.json()) as QuestionCreateResponse & { detail?: string };
      if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`);
      if (!data.id) throw new Error("Keine ID erhalten.");
      questionId = data.id;
      questionSlug = data.slug;
    } catch (err) {
      setError(`Fehler: ${String(err)}`);
      setLoading(false);
      return;
    }

    // 2. Forecast erzeugen (mit Sprache)
    let forecastSlug: string | null | undefined;
    try {
      const res = await fetch(
        `/api/questions/${questionId}/forecast?method_version=v0.1.0&language=${language}`,
        { method: "POST", headers: { Accept: "application/json", ...authHeaders } },
      );
      const data = (await res.json()) as ForecastCreateResponse;
      if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`);
      forecastSlug = data.question?.slug ?? data.question?.id ?? null;
    } catch (err) {
      setError(`Forecast-Fehler: ${String(err)}`);
      setLoading(false);
      return;
    }

    router.push(`/forecast/${forecastSlug ?? questionSlug ?? questionId}`);
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {/* Frage-Eingabe */}
      <div className="relative">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (question.trim() && !loading) {
                handleSubmit(e as unknown as React.FormEvent);
              }
            }
          }}
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
  );
}
