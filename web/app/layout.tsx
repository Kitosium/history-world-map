import localFont from "next/font/local";
import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";

const googleSans = localFont({
  src: [
    { path: "./fonts/GoogleSansFlex-400.ttf", weight: "400", style: "normal" },
    { path: "./fonts/GoogleSansFlex-500.ttf", weight: "500", style: "normal" },
    { path: "./fonts/GoogleSansFlex-600.ttf", weight: "600", style: "normal" },
    { path: "./fonts/GoogleSansFlex-700.ttf", weight: "700", style: "normal" }
  ],
  variable: "--font-google-sans",
  display: "swap",
  fallback: ["system-ui", "sans-serif"]
});

const materialSymbols = localFont({
  src: "./fonts/MaterialSymbolsRounded.ttf",
  weight: "400",
  style: "normal",
  variable: "--font-material-symbols",
  display: "block",
  fallback: ["sans-serif"]
});

export const metadata: Metadata = {
  title: "History Map — Atlas of Time",
  description:
    "A spatio-temporal atlas of historical polities, empires and civilizations from 3500 BCE to 2026 CE."
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#242b29"
};

const themeScript = `(function(){try{var t=localStorage.getItem("hm-theme");if(t!=="light"&&t!=="dark"){t="dark";}document.documentElement.dataset.theme=t;}catch(e){document.documentElement.dataset.theme="dark";}})();`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      data-theme="dark"
      suppressHydrationWarning
      className={`${googleSans.variable} ${materialSymbols.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
