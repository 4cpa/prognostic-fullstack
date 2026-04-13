import type { Metadata, Viewport } from "next";
import "./globals.css";

const BASE_URL = "https://4cpa.org";
const TITLE = "4CPA Prognostic Engine";
const DESCRIPTION =
  "Stelle eine Frage – erhalte einen KI-gestützten Forecast. Prognostics für Politik, Wirtschaft, Sport, Technologie und mehr. See tomorrow, today.";
const OG_IMAGE = `${BASE_URL}/social-preview.png`;

export const metadata: Metadata = {
  metadataBase: new URL(BASE_URL),

  // ── Basis ────────────────────────────────────────────────────────────────
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
  alternates: { canonical: BASE_URL },

  // ── Open Graph — WhatsApp, Telegram, Signal, iMessage, Messenger ────────
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

  // ── Twitter / X Card — auch von diversen Apps als Fallback genutzt ──────
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

  // ── Apple / iOS iMessage & Safari ────────────────────────────────────────
  appleWebApp: {
    capable: true,
    title: TITLE,
    statusBarStyle: "black-translucent",
    startupImage: OG_IMAGE,
  },

  // ── Icons — Favicon, Apple Touch Icon, Android ───────────────────────────
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

  // ── Weitere Plattform-Hints ───────────────────────────────────────────────
  category: "technology",
  classification: "Forecast / Prediction Tool",
  referrer: "strict-origin-when-cross-origin",
  formatDetection: {
    telephone: false,
    email: false,
    address: false,
  },
};

// Viewport separat exportieren (Next.js 14+ Anforderung)
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
        {/* iMessage / iOS Link-Preview: explizite og:image-Tags als Fallback */}
        <meta property="og:image" content={OG_IMAGE} />
        <meta property="og:image:secure_url" content={OG_IMAGE} />
        <meta property="og:image:type" content="image/png" />
        <meta property="og:image:width" content="1200" />
        <meta property="og:image:height" content="630" />
        <meta property="og:image:alt" content="4CPA Prognostic Engine" />

        {/* WhatsApp liest og:image:url als explizites Attribut */}
        <meta property="og:image:url" content={OG_IMAGE} />

        {/* Android / Chrome PWA Manifest */}
        <link rel="manifest" href="/manifest.json" />

        {/* Microsoft Tiles (Windows / Edge) */}
        <meta name="msapplication-TileColor" content="#0f172a" />
        <meta name="msapplication-TileImage" content="/icon.png" />
        <meta name="msapplication-config" content="none" />
      </head>
      <body>{children}</body>
    </html>
  );
}
