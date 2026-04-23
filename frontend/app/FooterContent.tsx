"use client";

import { useLanguage, type LangCode } from "./language-context";

const FOOTER_T: Record<LangCode, { disclaimer: string; license: string; noCommercial: string; sharing: string; donate: string }> = {
  de: {
    disclaimer:
      "Eingaben (Fragen) sowie die generierten Forecasts werden in einer Datenbank gespeichert und zur Analyse und Qualitätsverbesserung genutzt. Bitte keine personenbezogenen Daten eingeben.",
    license: "Inhalte lizenziert unter",
    sharing: "Weitergabe mit Quellenangabe erlaubt",
    noCommercial: "Keine kommerzielle Nutzung",
    donate: "Unterstütze dieses Projekt",
  },
  en: {
    disclaimer:
      "Inputs (questions) and generated forecasts are stored in a database and used for analysis and quality improvement. Please do not enter personal data.",
    license: "Content licensed under",
    sharing: "Sharing with attribution permitted",
    noCommercial: "No commercial use",
    donate: "Support this project",
  },
  fr: {
    disclaimer:
      "Les saisies (questions) et les prévisions générées sont stockées dans une base de données et utilisées à des fins d'analyse et d'amélioration de la qualité. Veuillez ne pas saisir de données personnelles.",
    license: "Contenu sous licence",
    sharing: "Partage avec attribution autorisé",
    noCommercial: "Pas d'utilisation commerciale",
    donate: "Soutenir ce projet",
  },
  it: {
    disclaimer:
      "Le domande inserite e le previsioni generate vengono archiviate in un database e utilizzate per analisi e miglioramento della qualità. Si prega di non inserire dati personali.",
    license: "Contenuto sotto licenza",
    sharing: "Condivisione con attribuzione consentita",
    noCommercial: "Nessun uso commerciale",
    donate: "Supporta questo progetto",
  },
  es: {
    disclaimer:
      "Las entradas (preguntas) y las predicciones generadas se almacenan en una base de datos y se utilizan para análisis y mejora de la calidad. Por favor, no introduzca datos personales.",
    license: "Contenido bajo licencia",
    sharing: "Compartir con atribución permitido",
    noCommercial: "Sin uso comercial",
    donate: "Apoya este proyecto",
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

      {/* Links: GitHub + Ko-fi */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginTop: "1rem" }}>

      {/* GitHub */}
      <a
        href="https://github.com/4cpa/prognostic-fullstack"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="GitHub Repository"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.35rem",
          backgroundColor: "#1e293b",
          color: "#fff",
          fontSize: "0.7rem",
          fontWeight: 600,
          padding: "0.3rem 0.75rem",
          borderRadius: "0.4rem",
          textDecoration: "none",
          whiteSpace: "nowrap",
        }}
      >
        {/* GitHub Octocat logo */}
        <svg width="14" height="14" viewBox="0 0 98 96" fill="currentColor" aria-hidden="true" focusable="false">
          <path fillRule="evenodd" clipRule="evenodd" d="M48.854 0C21.839 0 0 22 0 49.217c0 21.756 13.993 40.172 33.405 46.69 2.427.49 3.316-1.059 3.316-2.362 0-1.141-.08-5.052-.08-9.127-13.59 2.934-16.42-5.867-16.42-5.867-2.184-5.704-5.42-7.17-5.42-7.17-4.448-3.015.324-3.015.324-3.015 4.934.326 7.523 5.052 7.523 5.052 4.367 7.496 11.404 5.378 14.235 4.074.404-3.178 1.699-5.378 3.074-6.6-10.839-1.141-22.243-5.378-22.243-24.283 0-5.378 1.94-9.778 5.014-13.2-.485-1.222-2.184-6.275.486-13.038 0 0 4.125-1.304 13.426 5.052a46.97 46.97 0 0 1 12.214-1.63c4.125 0 8.33.571 12.213 1.63 9.302-6.356 13.427-5.052 13.427-5.052 2.67 6.763.97 11.816.485 13.038 3.155 3.422 5.015 7.822 5.015 13.2 0 18.905-11.404 23.06-22.324 24.283 1.78 1.548 3.316 4.481 3.316 9.126 0 6.6-.08 11.897-.08 13.526 0 1.304.89 2.853 3.316 2.364 19.412-6.52 33.405-24.935 33.405-46.691C97.707 22 75.788 0 48.854 0z"/>
        </svg>
        GitHub
      </a>

      {/* Ko-fi Spende */}
      <a
        href="https://ko-fi.com/E1E11XU5UD"
        target="_blank"
        rel="noopener noreferrer"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.35rem",
          backgroundColor: "#72a4f2",
          color: "#fff",
          fontSize: "0.7rem",
          fontWeight: 600,
          padding: "0.3rem 0.75rem",
          borderRadius: "0.4rem",
          textDecoration: "none",
        }}
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">
          <path d="M23.881 8.948c-.773-4.085-4.859-4.593-4.859-4.593H.723c-.604 0-.679.798-.679.798s-.082 7.324-.022 11.822c.164 2.424 2.586 2.672 2.586 2.672s8.267-.023 11.966-.049c2.438-.426 2.683-2.566 2.658-3.734 4.352.24 7.422-2.831 6.649-6.916zm-11.062 3.511c-1.246 1.453-4.011 3.976-4.011 3.976s-.121.119-.31.023c-.076-.057-.108-.09-.108-.09-.443-.441-3.368-3.049-4.034-3.954-.709-.965-1.041-2.7-.091-3.71.951-1.01 3.005-1.086 4.363.407 0 0 1.565-1.782 3.468-.963 1.904.82 1.832 3.011.723 4.311zm6.173.478c-.928.116-1.682.028-1.682.028V7.284h1.77s1.971.551 1.971 2.638c0 1.913-.985 2.667-2.059 3.015z"/>
        </svg>
        {t.donate}
      </a>

      {/* Twint Spende */}
      <a
        href="https://go.twint.ch/1/e/tw?tw=acq.x1hm6cyuR8u17Wn6-3sv7bblhwQU4Vf6PwXkjpR-X-HMLlMgKKzCFyPCjp7R-llu"
        target="_blank"
        rel="noopener noreferrer"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.4rem",
          backgroundColor: "#FFCC00",
          color: "#000",
          fontSize: "0.7rem",
          fontWeight: 800,
          padding: "0.3rem 0.75rem",
          borderRadius: "0.4rem",
          textDecoration: "none",
          letterSpacing: "0.06em",
          whiteSpace: "nowrap",
        }}
      >
        {/* TWINT T-Lettermark */}
        <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">
          <path d="M2 3h20v4.5h-8v13.5h-4V7.5H2z"/>
        </svg>
        TWINT
      </a>

      {/* Transivroom */}
      <a
        href="https://www.transivroom.ch"
        target="_blank"
        rel="noopener noreferrer"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.35rem",
          backgroundColor: "#dc2626",
          color: "#fff",
          fontSize: "0.7rem",
          fontWeight: 600,
          padding: "0.3rem 0.9rem",
          borderRadius: "0.4rem",
          textDecoration: "none",
          whiteSpace: "nowrap",
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/transivroom-icon.png" alt="" width={14} height={14} style={{ filter: "brightness(0) invert(1) brightness(2)", flexShrink: 0 }} />
        transivroom
      </a>

      </div>
    </>
  );
}
