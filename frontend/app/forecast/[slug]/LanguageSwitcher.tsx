"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const LANGUAGES = [
  { code: "de", flag: "🇩🇪", label: "DE", nativeName: "Deutsch" },
  { code: "en", flag: "🇬🇧", label: "EN", nativeName: "English" },
  { code: "it", flag: "🇮🇹", label: "IT", nativeName: "Italiano" },
  { code: "fr", flag: "🇫🇷", label: "FR", nativeName: "Français" },
  { code: "es", flag: "🇪🇸", label: "ES", nativeName: "Español" },
] as const;

type Props = {
  questionId: string;
  currentLanguage: string;
};

export default function LanguageSwitcher({ questionId, currentLanguage }: Props) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(currentLanguage.toLowerCase().slice(0, 2));

  async function switchLanguage(langCode: string) {
    if (langCode === active || loading) return;
    setLoading(true);
    setActive(langCode);

    try {
      await fetch(
        `/api/questions/${questionId}/forecast?method_version=v0.1.0&language=${langCode}`,
        { method: "POST", headers: { Accept: "application/json" } },
      );
    } catch {
      // best-effort — even on error, refresh to show whatever is stored
    }

    router.refresh();
    setLoading(false);
  }

  return (
    <fieldset className="border-0 p-0 mb-6">
      <legend className="mb-2 text-xs font-medium text-slate-600">
        {active === "de" ? "Analysesprache" :
         active === "en" ? "Analysis language" :
         active === "fr" ? "Langue d'analyse" :
         active === "it" ? "Lingua di analisi" :
         "Idioma del análisis"}
      </legend>
      <div className="flex flex-wrap gap-2">
        {LANGUAGES.map((lang) => {
          const isCurrent = lang.code === active;
          return (
            <button
              key={lang.code}
              type="button"
              onClick={() => switchLanguage(lang.code)}
              disabled={loading}
              aria-pressed={isCurrent}
              aria-label={`${lang.nativeName}${isCurrent ? " (aktiv)" : ""}`}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition min-h-[44px] disabled:opacity-60 ${
                isCurrent
                  ? "bg-slate-900 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-800"
              }`}
            >
              <span aria-hidden="true">{lang.flag}</span>
              <span>{lang.label}</span>
              {loading && isCurrent && (
                <svg
                  className="h-3 w-3 animate-spin ml-1"
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden="true"
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              )}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
