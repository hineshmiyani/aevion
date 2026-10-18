import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans_Condensed, Newsreader } from "next/font/google";
import "./globals.css";
import { themeScript } from "@/lib/theme";

// Newsreader for questions and answers (a reading serif with optical sizes), IBM Plex Sans
// Condensed for the interface and the map's labels, Plex Mono only for real code.
const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  axes: ["opsz"],
  style: ["normal", "italic"],
});
const plexCondensed = IBM_Plex_Sans_Condensed({
  variable: "--font-plex-condensed",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});
const plexMono = IBM_Plex_Mono({ variable: "--font-plex-mono", subsets: ["latin"], weight: ["400", "500"] });

export const metadata: Metadata = {
  title: "Aevion · Company brain on FalkorDB",
  description:
    "Ask how the FalkorDB project works: who knows what, why it was decided, what changed. Every answer shows the path through the graph that proves it.",
};

export const viewport: Viewport = {
  colorScheme: "light dark",
  themeColor: "#ffffff",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" suppressHydrationWarning className={`${newsreader.variable} ${plexCondensed.variable} ${plexMono.variable} h-full antialiased`}>
      <head><script dangerouslySetInnerHTML={{ __html: themeScript }} /></head>
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
