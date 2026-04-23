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
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/icons/icon-email.svg" alt="" width={15} height={15} />
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
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "center", gap: "0.6rem", marginTop: "1rem" }}>

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
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/icons/icon-github.svg" alt="" width={14} height={14} />
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
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/icons/icon-kofi.svg" alt="" width={13} height={13} />
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
          gap: "0.35rem",
          backgroundColor: "#000",
          color: "#fff",
          fontSize: "0.7rem",
          fontWeight: 700,
          padding: "0.3rem 0.75rem",
          borderRadius: "0.4rem",
          textDecoration: "none",
          whiteSpace: "nowrap",
          letterSpacing: "0.05em",
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/icons/icon-twint.svg" alt="" width={13} height={13} />
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
