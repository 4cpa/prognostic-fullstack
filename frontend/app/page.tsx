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
      className="flex flex-1 flex-col items-center justify-center px-4 py-12 sm:py-16"
    >
      {/* JSON-LD strukturierte Daten für Google */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <div className="w-full max-w-2xl">
        <HomeForm />
      </div>
    </main>
  );
}
