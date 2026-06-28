import type { Metadata } from "next";
import { Space_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Dissio",
  description: "AI flow coach for Public Forum debaters",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Dissio",
  },
  other: {
    "mobile-web-app-capable": "yes",
    "msapplication-TileColor": "#7c6cfc",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${spaceGrotesk.variable} ${jetbrainsMono.variable} h-full antialiased`}
      suppressHydrationWarning
      data-scroll-behavior="smooth"
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                const theme = localStorage.getItem('dissio-theme') || localStorage.getItem('roundlab-theme') || 'dark';
                document.documentElement.classList.add(theme);
              })();
            `,
          }}
        />
      </head>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        {/* Ambient gradient mesh — fixed behind all content */}
        <div
          className="pointer-events-none fixed inset-0 overflow-hidden"
          aria-hidden="true"
          style={{
            background: [
              "radial-gradient(ellipse 55% 40% at 12% -8%, oklch(0.510 0.156 278 / 0.08) 0%, transparent 70%)",
              "radial-gradient(ellipse 42% 32% at 88% -6%, oklch(0.780 0.140 200 / 0.06) 0%, transparent 65%)",
              "radial-gradient(ellipse 70% 50% at 50% 110%, oklch(0.510 0.156 278 / 0.03) 0%, transparent 70%)",
            ].join(", "),
          }}
        />
        {children}
      </body>
    </html>
  );
}
