import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "OjaBulk — Pool your money. Buy at wholesale price.",
  description:
    "Trust infrastructure for group procurement. OjaBulk removes the human intermediary from pooled buying, so no one can steal the pool and no one is denied a refund.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${spaceGrotesk.variable} font-sans bg-cream text-charcoal antialiased`}
      >
        {children}
      </body>
    </html>
  );
}