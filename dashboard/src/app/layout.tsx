import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Pulse — Instagram Automation Dashboard",
  description: "Autonomous AI Instagram media system. Research, design, write, schedule and publish premium AI news carousels daily.",
  keywords: ["AI news", "Instagram automation", "AI media", "social media", "AI carousel"],
  authors: [{ name: "AI Pulse" }],
  openGraph: {
    title: "AI Pulse Dashboard",
    description: "Autonomous AI Instagram Automation System",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Montserrat:wght@400;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}
