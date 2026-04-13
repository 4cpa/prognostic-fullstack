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
  forecast?: { id?: string | null } | null;
  error?: string | null;
};

export default function HomeForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const form = e.currentTarget;
    const title = (form.elements.namedItem("title") as HTMLInputElement).value.trim();
    const description = (
      form.elements.namedItem("description") as HTMLTextAreaElement
    ).value.trim();
    const resolveAt = (
      form.elements.namedItem("resolve_at") as HTMLInputElement
    ).value.trim();
    const resolutionCriteria = (
      form.elements.namedItem("resolution_criteria") as HTMLTextAreaElement
    ).value.trim();

    if (!title || !description || !resolveAt || !resolutionCriteria) {
      setError("Bitte alle Felder ausfüllen.");
      setLoading(false);
      return;
    }

    const apiKey = getStoredApiKey();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    if (apiKey) {
      headers["X-Anthropic-Key"] = apiKey;
    }

    // 1. Frage anlegen
    let questionId: string;
    let questionSlug: string | null | undefined;
    try {
      const questionRes = await fetch("/api/questions", {
        method: "POST",
        headers,
        body: JSON.stringify({ title, description, resolve_at: resolveAt, resolution_criteria: resolutionCriteria }),
      });
      const questionData = (await questionRes.json()) as QuestionCreateResponse & { detail?: string };
      if (!questionRes.ok) {
        throw new Error(questionData.detail ?? `HTTP ${questionRes.status}`);
      }
      if (!questionData.id) {
        throw new Error("Frage angelegt, aber keine ID erhalten.");
      }
      questionId = questionData.id;
      questionSlug = questionData.slug;
    } catch (err) {
      setError(`Frage konnte nicht angelegt werden: ${String(err)}`);
      setLoading(false);
      return;
    }

    // 2. Forecast erzeugen
    let forecastSlug: string | null | undefined;
    try {
      const forecastRes = await fetch(
        `/api/questions/${questionId}/forecast?method_version=v0.1.0`,
        { method: "POST", headers: { Accept: "application/json", ...(apiKey ? { "X-Anthropic-Key": apiKey } : {}) } },
      );
      const forecastData = (await forecastRes.json()) as ForecastCreateResponse & { detail?: string };
      if (!forecastRes.ok) {
        throw new Error(forecastData.detail ?? `HTTP ${forecastRes.status}`);
      }
      forecastSlug =
        forecastData.question?.slug ??
        forecastData.question?.id ??
        null;
    } catch (err) {
      setError(`Forecast konnte nicht erzeugt werden: ${String(err)}`);
      setLoading(false);
      return;
    }

    const target = forecastSlug ?? questionSlug ?? questionId;
    router.push(`/forecast/${target}`);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

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
        disabled={loading}
        className="inline-flex rounded-xl bg-slate-900 px-5 py-3 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
      >
        {loading ? "Wird verarbeitet…" : "Frage anlegen und Forecast erzeugen"}
      </button>
    </form>
  );
}
