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

      {/* Twint Spende – offizielles Logo von twint.ch */}
      <a
        href="https://go.twint.ch/1/e/tw?tw=acq.x1hm6cyuR8u17Wn6-3sv7bblhwQU4Vf6PwXkjpR-X-HMLlMgKKzCFyPCjp7R-llu"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="TWINT Spende"
        style={{
          display: "inline-block",
          lineHeight: 0,
          borderRadius: "0.4rem",
          overflow: "hidden",
          textDecoration: "none",
          flexShrink: 0,
          verticalAlign: "middle",
        }}
      >
        <svg height="24" width="63" viewBox="0 0 153 58" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="twint-rg-a" cx="22.357%" cy="8.811%" gradientTransform="matrix(1 0 0 .91756 0 .007)" r="113.202%">
              <stop offset="0" stopColor="#fc0"/><stop offset=".09157" stopColor="#ffc800"/>
              <stop offset=".1739" stopColor="#ffbd00"/><stop offset=".2528" stopColor="#ffab00"/>
              <stop offset=".3295" stopColor="#ff9100"/><stop offset=".4046" stopColor="#ff7000"/>
              <stop offset=".4786" stopColor="#ff4700"/><stop offset=".5503" stopColor="#ff1800"/>
              <stop offset=".5822" stopColor="#f00"/><stop offset="1" stopColor="#f00"/>
            </radialGradient>
            <radialGradient id="twint-rg-b" cx="2.552%" cy="14.432%" gradientTransform="matrix(1 0 0 .68117 0 .046)" r="139.457%">
              <stop offset="0" stopColor="#00b4e6"/><stop offset=".201" stopColor="#00b0e3"/>
              <stop offset=".3898" stopColor="#01a5db"/><stop offset=".5737" stopColor="#0292cd"/>
              <stop offset=".7546" stopColor="#0377ba"/><stop offset=".9316" stopColor="#0455a1"/>
              <stop offset="1" stopColor="#054696"/>
            </radialGradient>
          </defs>
          <g fill="none">
            <path d="m150.90357 58h-148.78081678c-1.18229293 0-2.12275322-.9406858-2.12275322-2.1232623v-53.75347542c0-1.18257646.94046029-2.12326228 2.12275322-2.12326228h148.75394678c1.182293 0 2.1233.94068582 2.1233 2.12326228v53.75347542c.026324 1.1825765-.941007 2.1232623-2.09643 2.1232623z" fill="#000"/>
            <path d="m48 39.3882699c0 .5589601-.4019746 1.2510059-.8843441 1.5171773l-17.2313118 9.8749613c-.4823695.2927887-1.2863187.2927887-1.7686882 0l-17.2313118-9.8749613c-.4823695-.2927886-.8843441-.9582172-.8843441-1.5171773v-19.7765398c0-.5589601.4019746-1.2510059.8843441-1.5171773l17.2313118-9.87496134c.4823695-.29278861 1.2863187-.29278861 1.7686882 0l17.2313118 9.87496134c.4823695.2927886.8843441.9582172.8843441 1.5171773z" fill="#fff"/>
            <g fill="#fff" transform="translate(57 20)">
              <path d="m85.839.684h-15.48v3.605h5.536v15.474h4.381v-15.474h5.563z"/>
              <path d="m15.534.684h-15.48v3.605h5.563v15.474h4.381v-15.474h5.536z"/>
              <path d="m60.334375.07894737c-4.864375 0-7.57875 3.05263158-7.57875 7.44736842v12.23684211h4.326875v-12.34210527c0-1.92105263 1.155625-3.39473684 3.305625-3.39473684 2.123125 0 3.27875 1.7368421 3.27875 3.39473684v12.34210527h4.326875v-12.23684211c0-4.39473684-2.795-7.44736842-7.659375-7.44736842z"/>
              <path d="m43.968.684v19.079h4.353v-19.079z"/>
              <path d="m29.294 8.263.161.842 4.058 10.658h1.774l5.536-19.079h-4.273l-2.661 10.027-.134 1.078-.215-1.078-3.548-10.027h-1.397l-3.521 10.027-.215 1.078-.161-1.078-2.634-10.027h-4.273l5.537 19.079h1.773l4.058-10.658z"/>
            </g>
            <g transform="translate(14 20)">
              <path d="m23.0029412 9.12820513-4.4205883 6.30769227-2.2764705-3.3846153 2.6205882-3.79487184c.4764706-.66666667 1.5352941-2.53846154.317647-5.07692308-.9794117-2.05128205-3.0970588-3.05128205-4.95-3.05128205-1.8529411 0-3.8911764.92307692-4.94999995 3.05128205-1.21764706 2.43589744-.15882353 4.35897436.29117647 5 0 0 1.45588238 2.07692312 2.67352938 3.82051282l1.9852941 2.7692308 2.9647059 4.3846154c.0264706.025641.5029412.7179487 1.3235294.7179487.7941177 0 1.2705883-.6923077 1.35-.7692308l6.9617647-9.97435897zm-8.7088236.15384615s-1.1647058-1.71794872-1.9058823-2.8974359c-.8205882-1.28205128.1058823-3.17948717 1.9058823-3.17948717 1.8264706 0 2.7264706 1.89743589 1.9058824 3.17948717-.7411765 1.20512821-1.9058824 2.8974359-1.9058824 2.8974359z" fill="url(#twint-rg-a)"/>
              <path d="m10.0058824 15.2307692-4.36764711-5.92307689s-1.16470588-1.71794872-1.90588235-2.8974359c-.82058823-1.28205128.10588235-3.17948718 1.90588235-3.17948718.2382353 0 .45.02564103.63529412.07692308l1.53529412-2.71794872c-.71470588-.28205128-1.45588235-.43589744-2.17058824-.43589744-1.85294117 0-3.89117647.92307693-4.95 3.05128206-1.21764706 2.43589743-.15882352 4.35897435.29117648 5l7.62352941 10.94871799c.05294117.1025641.55588235.7948717 1.35.7948717.82058822 0 1.27058822-.6666666 1.35000002-.7692307l2.3029412-3.3846154-1.9852942-2.8205128z" fill="url(#twint-rg-b)"/>
            </g>
          </g>
        </svg>
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
