"use client";

import { useLanguage, type LangCode } from "./language-context";

const FOOTER_T: Record<LangCode, { disclaimer: string; license: string; noCommercial: string; sharing: string }> = {
  de: {
    disclaimer:
      "Eingaben (Fragen) sowie die generierten Forecasts werden in einer Datenbank gespeichert und zur Analyse und Qualitätsverbesserung genutzt. Bitte keine personenbezogenen Daten eingeben.",
    license: "Inhalte lizenziert unter",
    sharing: "Weitergabe mit Quellenangabe erlaubt",
    noCommercial: "Keine kommerzielle Nutzung",
  },
  en: {
    disclaimer:
      "Inputs (questions) and generated forecasts are stored in a database and used for analysis and quality improvement. Please do not enter personal data.",
    license: "Content licensed under",
    sharing: "Sharing with attribution permitted",
    noCommercial: "No commercial use",
  },
  fr: {
    disclaimer:
      "Les saisies (questions) et les prévisions générées sont stockées dans une base de données et utilisées à des fins d'analyse et d'amélioration de la qualité. Veuillez ne pas saisir de données personnelles.",
    license: "Contenu sous licence",
    sharing: "Partage avec attribution autorisé",
    noCommercial: "Pas d'utilisation commerciale",
  },
  it: {
    disclaimer:
      "Le domande inserite e le previsioni generate vengono archiviate in un database e utilizzate per analisi e miglioramento della qualità. Si prega di non inserire dati personali.",
    license: "Contenuto sotto licenza",
    sharing: "Condivisione con attribuzione consentita",
    noCommercial: "Nessun uso commerciale",
  },
  es: {
    disclaimer:
      "Las entradas (preguntas) y las predicciones generadas se almacenan en una base de datos y se utilizan para análisis y mejora de la calidad. Por favor, no introduzca datos personales.",
    license: "Contenido bajo licencia",
    sharing: "Compartir con atribución permitido",
    noCommercial: "Sin uso comercial",
  },
};

export default function FooterContent() {
  const { language } = useLanguage();
  const t = FOOTER_T[language];

  return (
    <>
      {/* Impressum */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span>Transivroom Division 2026</span>
        <a
          href="mailto:admin@4cpa.ch?subject=Question%20for%204cpa"
          aria-label="E-Mail an admin@4cpa.ch senden"
          style={{ color: "#94a3b8", lineHeight: 1, display: "inline-flex", alignItems: "center" }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            focusable="false"
          >
            <rect width="20" height="16" x="2" y="4" rx="2" />
            <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
          </svg>
        </a>
      </div>

      {/* Datenschutz-Disclaimer */}
      <p style={{ maxWidth: "36rem", lineHeight: "1.6", color: "#94a3b8", fontSize: "0.75rem" }}>
        {t.disclaimer}
      </p>

      {/* Lizenz */}
      <p style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
        {t.license}{" "}
        <a
          href="https://creativecommons.org/licenses/by-nc/4.0/"
          target="_blank"
          rel="noopener noreferrer license"
          style={{ color: "#cbd5e1", textDecoration: "underline" }}
        >
          CC BY-NC 4.0
        </a>
        {" "}· {t.sharing} · {t.noCommercial}
      </p>
    </>
  );
}
