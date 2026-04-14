import HomeForm from "./HomeForm";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": "https://4cpa.org/#website",
      "url": "https://4cpa.org",
      "name": "4CPA Prognostic Engine",
      "description":
        "KI-gestütztes Prognose-Tool: Stelle eine Frage zu Politik, Wirtschaft, Sport oder Technologie und erhalte einen datenbasierten Forecast mit Wahrscheinlichkeit, Szenarien und Quellenanalyse.",
      "inLanguage": ["de", "en", "fr", "it", "es"],
      "potentialAction": {
        "@type": "SearchAction",
        "target": {
          "@type": "EntryPoint",
          "urlTemplate": "https://4cpa.org/?q={search_term_string}",
        },
        "query-input": "required name=search_term_string",
      },
    },
    {
      "@type": "WebApplication",
      "@id": "https://4cpa.org/#app",
      "name": "4CPA Prognostic Engine",
      "url": "https://4cpa.org",
      "applicationCategory": "UtilityApplication",
      "operatingSystem": "All",
      "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "CHF",
      },
      "description":
        "Gib eine Prognosefrage ein und erhalte sofort einen KI-gestützten Forecast: kalibrierte Wahrscheinlichkeit, konkrete Szenarien, Pro/Contra-Signale und analysierte Quellen.",
      "featureList": [
        "KI-Prognosen mit Wahrscheinlichkeitsangabe",
        "Pro- und Contra-Signalanalyse",
        "Konkrete Szenarien für offene Fragen",
        "Quellenbasierte Analyse",
        "Verfügbar in Deutsch, Englisch, Französisch, Italienisch, Spanisch",
      ],
    },
    {
      "@type": "Organization",
      "@id": "https://4cpa.org/#org",
      "name": "Transivroom",
      "url": "https://4cpa.org",
      "contactPoint": {
        "@type": "ContactPoint",
        "email": "admin@4cpa.ch",
        "contactType": "customer support",
      },
    },
  ],
};

export default function HomePage() {
  return (
    <main
      id="main-content"
      className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4"
    >
      {/* JSON-LD strukturierte Daten für Google */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-slate-950">
            4cpa Prognostic
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Frage stellen — KI-Forecast erhalten
          </p>
        </div>

        {/* Formular */}
        <HomeForm />

        {/* SEO-Text: für Google sichtbar, für User dezent */}
        <div className="mt-10 border-t border-slate-200 pt-8 space-y-4 text-sm text-slate-500 leading-6">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-400">
            Wie es funktioniert
          </h2>
          <div className="grid gap-3 sm:grid-cols-3 text-xs text-slate-400">
            <div>
              <p className="font-medium text-slate-500 mb-1">Frage eingeben</p>
              <p>Stelle eine beliebige Prognosefrage — z.&nbsp;B. zu Politik, Wirtschaft, Sport oder Technologie.</p>
            </div>
            <div>
              <p className="font-medium text-slate-500 mb-1">KI analysiert</p>
              <p>Die Engine recherchiert aktuelle Quellen, extrahiert Signale und berechnet eine kalibrierte Wahrscheinlichkeit.</p>
            </div>
            <div>
              <p className="font-medium text-slate-500 mb-1">Forecast erhalten</p>
              <p>Du siehst Pro/Contra-Argumente, konkrete Szenarien und alle analysierten Quellen — in deiner Sprache.</p>
            </div>
          </div>
          <p className="text-xs text-slate-400">
            Verfügbar in Deutsch, English, Français, Italiano und Español.
            Prognosen für Wahlen, Märkte, Geopolitik, Klimaereignisse und mehr.
          </p>
        </div>
      </div>
    </main>
  );
}
