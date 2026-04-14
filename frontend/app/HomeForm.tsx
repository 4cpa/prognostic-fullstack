"use client";

import { useId, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { useLanguage, type LangCode } from "./language-context";

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
  { code: "de", flag: "🇩🇪", nativeName: "Deutsch", label: "DE" },
  { code: "en", flag: "🇬🇧", nativeName: "English", label: "EN" },
  { code: "it", flag: "🇮🇹", nativeName: "Italiano", label: "IT" },
  { code: "fr", flag: "🇫🇷", nativeName: "Français", label: "FR" },
  { code: "es", flag: "🇪🇸", nativeName: "Español", label: "ES" },
] as const;

const UI: Record<
  LangCode,
  {
    tagline: string;
    questionLabel: string;
    questionHint: string;
    placeholder: string;
    langLegend: string;
    activeLabel: string;
    submitting: string;
    submitAriaLoading: string;
    submitAriaIdle: string;
    errorNotFound: string;
    errorServer: (status: number) => string;
    errorNetwork: string;
    howTitle: string;
    step1Title: string;
    step1: string;
    step2Title: string;
    step2: string;
    step3Title: string;
    step3: string;
    available: string;
  }
> = {
  de: {
    tagline: "Frage stellen — KI-Forecast erhalten",
    questionLabel: "Deine Prognosefrage",
    questionHint: "(Enter zum Absenden)",
    placeholder: "z. B. «Wird es 2026 einen Weltkrieg geben?»",
    langLegend: "Antwortsprache wählen",
    activeLabel: "(aktiv)",
    submitting: "Forecast wird berechnet, bitte warten…",
    submitAriaLoading: "Forecast wird berechnet…",
    submitAriaIdle: "Forecast erzeugen",
    errorNotFound: "Ressource nicht gefunden (404)",
    errorServer: (s) => `Serverfehler (${s})`,
    errorNetwork: "Verbindungsfehler",
    howTitle: "Wie es funktioniert",
    step1Title: "Frage eingeben",
    step1:
      "Stelle eine beliebige Prognosefrage — z.\u00a0B. zu Politik, Wirtschaft, Sport oder Technologie.",
    step2Title: "KI analysiert",
    step2:
      "Die Engine recherchiert aktuelle Quellen, extrahiert Signale und berechnet eine kalibrierte Wahrscheinlichkeit.",
    step3Title: "Forecast erhalten",
    step3:
      "Du siehst Pro/Contra-Argumente, konkrete Szenarien und alle analysierten Quellen — in deiner Sprache.",
    available:
      "Verfügbar in Deutsch, English, Français, Italiano und Español. Prognosen für Wahlen, Märkte, Geopolitik, Klimaereignisse und mehr.",
  },
  en: {
    tagline: "Ask a question — get an AI forecast",
    questionLabel: "Your forecast question",
    questionHint: "(Press Enter to submit)",
    placeholder: "e.g. «Will there be a world war in 2026?»",
    langLegend: "Choose answer language",
    activeLabel: "(active)",
    submitting: "Calculating forecast, please wait…",
    submitAriaLoading: "Calculating forecast…",
    submitAriaIdle: "Generate forecast",
    errorNotFound: "Resource not found (404)",
    errorServer: (s) => `Server error (${s})`,
    errorNetwork: "Connection error",
    howTitle: "How it works",
    step1Title: "Enter a question",
    step1:
      "Ask any forecast question — e.g. about politics, economy, sports or technology.",
    step2Title: "AI analyses",
    step2:
      "The engine searches current sources, extracts signals and calculates a calibrated probability.",
    step3Title: "Receive forecast",
    step3:
      "You see pro/contra arguments, concrete scenarios and all analysed sources — in your language.",
    available:
      "Available in German, English, French, Italian and Spanish. Forecasts for elections, markets, geopolitics, climate events and more.",
  },
  fr: {
    tagline: "Posez une question — obtenez une prévision IA",
    questionLabel: "Votre question de prévision",
    questionHint: "(Entrée pour soumettre)",
    placeholder: "p. ex. «Y aura-t-il une guerre mondiale en 2026\u00a0?»",
    langLegend: "Choisir la langue de réponse",
    activeLabel: "(actif)",
    submitting: "Calcul de la prévision en cours…",
    submitAriaLoading: "Calcul en cours…",
    submitAriaIdle: "Générer la prévision",
    errorNotFound: "Ressource introuvable (404)",
    errorServer: (s) => `Erreur serveur (${s})`,
    errorNetwork: "Erreur de connexion",
    howTitle: "Comment ça fonctionne",
    step1Title: "Entrer une question",
    step1:
      "Posez n'importe quelle question de prévision — p.\u00a0ex. sur la politique, l'économie, le sport ou la technologie.",
    step2Title: "L'IA analyse",
    step2:
      "Le moteur recherche des sources actuelles, extrait des signaux et calcule une probabilité calibrée.",
    step3Title: "Recevoir la prévision",
    step3:
      "Vous voyez les arguments pour/contre, des scénarios concrets et toutes les sources analysées — dans votre langue.",
    available:
      "Disponible en allemand, anglais, français, italien et espagnol. Prévisions pour les élections, marchés, géopolitique, événements climatiques et plus.",
  },
  it: {
    tagline: "Fai una domanda — ottieni una previsione IA",
    questionLabel: "La tua domanda di previsione",
    questionHint: "(Invio per inviare)",
    placeholder: "es. «Ci sarà una guerra mondiale nel 2026?»",
    langLegend: "Scegli la lingua della risposta",
    activeLabel: "(attivo)",
    submitting: "Calcolo previsione in corso…",
    submitAriaLoading: "Calcolo in corso…",
    submitAriaIdle: "Genera previsione",
    errorNotFound: "Risorsa non trovata (404)",
    errorServer: (s) => `Errore server (${s})`,
    errorNetwork: "Errore di connessione",
    howTitle: "Come funziona",
    step1Title: "Inserisci una domanda",
    step1:
      "Fai qualsiasi domanda di previsione — p.\u00a0es. su politica, economia, sport o tecnologia.",
    step2Title: "L'IA analizza",
    step2:
      "Il motore ricerca fonti attuali, estrae segnali e calcola una probabilità calibrata.",
    step3Title: "Ricevi la previsione",
    step3:
      "Vedi argomenti pro/contro, scenari concreti e tutte le fonti analizzate — nella tua lingua.",
    available:
      "Disponibile in tedesco, inglese, francese, italiano e spagnolo. Previsioni per elezioni, mercati, geopolitica, eventi climatici e altro.",
  },
  es: {
    tagline: "Haz una pregunta — obtén una predicción IA",
    questionLabel: "Tu pregunta de predicción",
    questionHint: "(Intro para enviar)",
    placeholder: "p.\u00a0ej. «¿Habrá una guerra mundial en 2026?»",
    langLegend: "Elegir idioma de respuesta",
    activeLabel: "(activo)",
    submitting: "Calculando predicción, por favor espera…",
    submitAriaLoading: "Calculando predicción…",
    submitAriaIdle: "Generar predicción",
    errorNotFound: "Recurso no encontrado (404)",
    errorServer: (s) => `Error del servidor (${s})`,
    errorNetwork: "Error de conexión",
    howTitle: "Cómo funciona",
    step1Title: "Introducir una pregunta",
    step1:
      "Haz cualquier pregunta de predicción — p.\u00a0ej. sobre política, economía, deporte o tecnología.",
    step2Title: "La IA analiza",
    step2:
      "El motor busca fuentes actuales, extrae señales y calcula una probabilidad calibrada.",
    step3Title: "Recibir predicción",
    step3:
      "Ves argumentos a favor/en contra, escenarios concretos y todas las fuentes analizadas — en tu idioma.",
    available:
      "Disponible en alemán, inglés, francés, italiano y español. Predicciones para elecciones, mercados, geopolítica, eventos climáticos y más.",
  },
};

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
  const { language, setLanguage } = useLanguage();
  const [error, setError] = useState<AppError | null>(null);
  const [loading, setLoading] = useState(false);

  const t = UI[language];

  const textareaId = useId();
  const errorId = useId();
  const statusId = useId();
  const liveRef = useRef<HTMLDivElement>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;

    setError(null);
    setLoading(true);

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
        setError({ kind: "http", status: 200, detail: t.errorServer(200) });
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

  const errorTitle =
    error == null
      ? null
      : error.kind === "http" && error.status === 404
      ? t.errorNotFound
      : error.kind === "http"
      ? t.errorServer(error.status)
      : t.errorNetwork;

  const errorDetail =
    error == null
      ? null
      : error.kind === "network"
      ? error.msg
      : error.detail;

  return (
    <div className="w-full space-y-4">
      {/* Tagline — reacts to language selection */}
      <div className="mb-8 flex items-center justify-center gap-5">
        <Image
          src="/icon.png"
          alt="4cpa logo"
          width={76}
          height={76}
          className="rounded-xl shrink-0 bg-slate-50"
          priority
        />
        <div className="text-left">
          <h1 className="text-4xl font-bold tracking-tight text-slate-950">
            4cpa Prognostic
          </h1>
          <p className="mt-1.5 text-sm text-slate-600">{t.tagline}</p>
        </div>
      </div>

      {/* Screen-reader live region */}
      <div
        ref={liveRef}
        id={statusId}
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {loading && t.submitting}
        {!loading && error && `${errorTitle}: ${errorDetail}`}
      </div>

      {/* Visible error */}
      {error && (
        <div
          id={errorId}
          role="alert"
          aria-atomic="true"
          className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900"
        >
          <p className="font-semibold">{errorTitle}</p>
          <p className="mt-1 text-xs text-red-700">{errorDetail}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="w-full" aria-busy={loading} noValidate>
        <label
          htmlFor={textareaId}
          className="mb-2 block text-sm font-medium text-slate-700"
        >
          {t.questionLabel}
          <span className="ml-1 text-slate-500 font-normal">{t.questionHint}</span>
        </label>

        <div className="relative">
          <textarea
            id={textareaId}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t.placeholder}
            rows={3}
            required
            disabled={loading}
            aria-required="true"
            aria-describedby={error ? errorId : undefined}
            aria-invalid={error != null ? "true" : undefined}
            className="w-full resize-none rounded-2xl border border-slate-200 bg-white px-5 py-4 pr-14 text-base text-slate-900 shadow-sm outline-none placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-300 disabled:opacity-60"
          />

          <button
            type="submit"
            disabled={!question.trim() || loading}
            aria-label={loading ? t.submitAriaLoading : t.submitAriaIdle}
            className="absolute bottom-3 right-3 flex h-11 w-11 items-center justify-center rounded-xl bg-slate-900 text-white transition hover:bg-slate-700 disabled:opacity-30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            {loading ? (
              <svg
                className="h-4 w-4 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
                focusable="false"
              >
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            ) : (
              <svg
                className="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                aria-hidden="true"
                focusable="false"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            )}
          </button>
        </div>

        <fieldset className="mt-4 border-0 p-0">
          <legend className="mb-2 text-xs font-medium text-slate-600">
            {t.langLegend}
          </legend>
          <div className="flex flex-wrap gap-2" role="group">
            {LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                type="button"
                onClick={() => setLanguage(lang.code)}
                aria-pressed={language === lang.code}
                aria-label={`${lang.nativeName}${language === lang.code ? ` ${t.activeLabel}` : ""}`}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition min-h-[44px] ${
                  language === lang.code
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-800"
                }`}
              >
                <span aria-hidden="true">{lang.flag}</span>
                <span>{lang.label}</span>
              </button>
            ))}
          </div>
        </fieldset>
      </form>

      {/* "How it works" — reacts to language selection */}
      <div className="mt-10 border-t border-slate-200 pt-8 space-y-4 text-sm text-slate-500 leading-6">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-400">
          {t.howTitle}
        </h2>
        <div className="grid gap-3 sm:grid-cols-3 text-xs text-slate-400">
          <div>
            <p className="font-medium text-slate-500 mb-1">{t.step1Title}</p>
            <p>{t.step1}</p>
          </div>
          <div>
            <p className="font-medium text-slate-500 mb-1">{t.step2Title}</p>
            <p>{t.step2}</p>
          </div>
          <div>
            <p className="font-medium text-slate-500 mb-1">{t.step3Title}</p>
            <p>{t.step3}</p>
          </div>
        </div>
        <p className="text-xs text-slate-400">{t.available}</p>
      </div>
    </div>
  );
}
