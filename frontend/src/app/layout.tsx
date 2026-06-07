import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RoundLab",
  description: "AI flow coach for Public Forum debaters",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                const theme = localStorage.getItem('roundlab-theme') || 'dark';
                document.documentElement.classList.add(theme);
              })();
            `,
          }}
        />
      </head>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        {/* Ambient gradient mesh — fixed behind all content, gives AI-lab depth */}
        <div
          className="pointer-events-none fixed inset-0 overflow-hidden"
          aria-hidden="true"
          style={{
            background: [
              "radial-gradient(ellipse 55% 40% at 12% -8%, oklch(0.510 0.156 278 / 0.10) 0%, transparent 70%)",
              "radial-gradient(ellipse 42% 32% at 88% -6%, oklch(0.780 0.140 200 / 0.07) 0%, transparent 65%)",
              "radial-gradient(ellipse 70% 50% at 50% 110%, oklch(0.510 0.156 278 / 0.04) 0%, transparent 70%)",
            ].join(", "),
          }}
        />
        {children}
      </body>
    </html>
  );
}
