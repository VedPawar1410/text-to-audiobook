import type { Metadata, Viewport } from "next";
import { Fraunces, Geist, Geist_Mono, Newsreader } from "next/font/google";
import { Nav } from "@/components/nav";
import "./globals.css";

// Display serif for headlines: theatrical, with optical sizing and a soft axis.
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["opsz", "SOFT"],
});

// Reading serif, designed for long-form text (used in the reader).
const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  axes: ["opsz"],
  style: ["normal", "italic"],
});

// UI sans + mono for labels and timecodes.
const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Narrate: every text, performed",
  description: "Turn any text into an expressive, multi-voice audiobook with read-along.",
};

// Phone browsers tint their toolbars to match the stage instead of default grey
export const viewport: Viewport = { themeColor: "#0b0908", colorScheme: "dark" };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${fraunces.variable} ${newsreader.variable} ${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        {/* Soft spotlight falling from above the stage */}
        <div
          aria-hidden
          className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_80%_60%_at_70%_-10%,rgb(255_181_71/0.09),transparent_60%)]"
        />
        <Nav />
        <div className="relative flex flex-1 flex-col">{children}</div>
      </body>
    </html>
  );
}
