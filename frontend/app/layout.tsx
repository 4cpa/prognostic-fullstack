import type { Metadata } from "next";
import "./globals.css";
import ApiKeyBanner from "./ApiKeyBanner";

export const metadata: Metadata = {
  metadataBase: new URL("https://4cpa.org"),
  title: "4CPA Prognostic Engine",
  description: "4cpa - see tomorrow, today",
  applicationName: "4CPA Prognostic Engine",
  openGraph: {
    title: "4CPA Prognostic Engine",
    description: "4cpa - see tomorrow, today",
    url: "https://4cpa.org",
    siteName: "4CPA Prognostic Engine",
    images: [
      {
        url: "/social-preview.png",
        width: 1200,
        height: 630,
        alt: "4CPA Prognostic Engine",
      },
    ],
    locale: "de_CH",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "4CPA Prognostic Engine",
    description: "4cpa - see tomorrow, today",
    images: ["/social-preview.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de">
      <body>
        <ApiKeyBanner />
        {children}
      </body>
    </html>
  );
}
