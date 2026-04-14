import type { Metadata, Viewport } from "next";
import "./globals.css";

const BASE_URL = "https://4cpa.org";
const TITLE = "4CPA Prognostic Engine";
const DESCRIPTION =
  "Stelle eine Frage – erhalte einen KI-gestützten Forecast. Prognostics für Politik, Wirtschaft, Sport, Technologie und mehr. See tomorrow, today.";
const OG_IMAGE = `${BASE_URL}/social-preview.png`;

export const metadata: Metadata = {
  metadataBase: new URL(BASE_URL),

  title: {
    default: TITLE,
    template: `%s · 4CPA Prognostic`,
  },
  description: DESCRIPTION,
  applicationName: TITLE,
  keywords: [
    "Prognose", "Forecast", "KI", "AI", "Prediction",
    "Politik", "Wirtschaft", "Sport", "Technologie",
    "4cpa", "Prognostic Engine",
  ],
  authors: [{ name: "4CPA", url: BASE_URL }],
  creator: "4CPA",
  publisher: "4CPA",
  robots: { index: true, follow: true },
  verification: {
    google: "Onz5ZMs_K6h_DErH5uJhQRIwKtXvyaKTTH7MLyj6bNs",
  },
  alternates: { canonical: BASE_URL },

  openGraph: {
    type: "website",
    url: BASE_URL,
    siteName: TITLE,
    title: TITLE,
    description: DESCRIPTION,
    locale: "de_CH",
    images: [
      {
        url: OG_IMAGE,
        secureUrl: OG_IMAGE,
        width: 1200,
        height: 630,
        alt: "4CPA Prognostic Engine – See tomorrow, today",
        type: "image/png",
      },
    ],
  },

  twitter: {
    card: "summary_large_image",
    site: "@4cpa",
    creator: "@4cpa",
    title: TITLE,
    description: DESCRIPTION,
    images: [
      {
        url: OG_IMAGE,
        alt: "4CPA Prognostic Engine",
        width: 1200,
        height: 630,
      },
    ],
  },

  appleWebApp: {
    capable: true,
    title: TITLE,
    statusBarStyle: "black-translucent",
    startupImage: OG_IMAGE,
  },

  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/icon.png", type: "image/png", sizes: "512x512" },
    ],
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
    shortcut: "/favicon.ico",
  },

  category: "technology",
  classification: "Forecast / Prediction Tool",
  referrer: "strict-origin-when-cross-origin",
  formatDetection: {
    telephone: false,
    email: false,
    address: false,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8fafc" },
    { media: "(prefers-color-scheme: dark)", color: "#0f172a" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de">
      <head>
        <meta property="og:image" content={OG_IMAGE} />
        <meta property="og:image:secure_url" content={OG_IMAGE} />
        <meta property="og:image:type" content="image/png" />
        <meta property="og:image:width" content="1200" />
        <meta property="og:image:height" content="630" />
        <meta property="og:image:alt" content="4CPA Prognostic Engine" />
        <meta property="og:image:url" content={OG_IMAGE} />
        <link rel="manifest" href="/manifest.json" />
        <meta name="msapplication-TileColor" content="#0f172a" />
        <meta name="msapplication-TileImage" content="/icon.png" />
        <meta name="msapplication-config" content="none" />
      </head>
      <body>
        {/* Skip-Navigation: für Tastatur- und Screenreader-Nutzer */}
        <a href="#main-content" className="skip-link">
          Zum Hauptinhalt springen
        </a>

        {children}

        <footer
          aria-label="Seiteninfos"
          style={{
            textAlign: "center",
            padding: "1.5rem 1rem 2rem",
            fontSize: "0.8125rem",
            color: "#64748b",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "0.75rem",
          }}
        >
          {/* Impressum */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span>Transivroom Division 2026</span>
            <a
              href="mailto:admin@4cpa.ch?subject=Question%20for%204cpa"
              aria-label="E-Mail an admin@4cpa.ch senden"
              style={{ color: "#64748b", lineHeight: 1, display: "inline-flex", alignItems: "center" }}
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
            Eingaben (Fragen) sowie die generierten Forecasts werden in einer Datenbank gespeichert
            und zur Analyse und Qualitätsverbesserung genutzt. Bitte keine personenbezogenen Daten eingeben.
          </p>

          {/* Lizenz */}
          <p style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
            Inhalte lizenziert unter{" "}
            <a
              href="https://creativecommons.org/licenses/by-nc/4.0/"
              target="_blank"
              rel="noopener noreferrer license"
              style={{ color: "#64748b", textDecoration: "underline" }}
            >
              CC BY-NC 4.0
            </a>
            {" "}· Weitergabe mit Quellenangabe erlaubt · Keine kommerzielle Nutzung
          </p>
        </footer>
      </body>
    </html>
  );
}
