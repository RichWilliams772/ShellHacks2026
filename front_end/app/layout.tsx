import type { Metadata } from "next";
import { Barlow, Barlow_Condensed } from "next/font/google";
import "./globals.css";

// Barlow comes from US highway/infrastructure signage — fitting for a grid planning tool.
const barlow = Barlow({
  variable: "--font-barlow",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const barlowCondensed = Barlow_Condensed({
  variable: "--font-barlow-condensed",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

export const metadata: Metadata = {
  title: "GridSync",
  description: "Find where the grid can build together.",
};

// Registration marks, like a printed sheet's crop marks - the same corner-bracket device
// OpportunityDetail.tsx uses for its section breaks, at page scale instead of section scale.
// Fixed and non-interactive, so it never competes with the map's own overlay controls.
function CornerMarks() {
  const corner = "absolute h-3.5 w-3.5 border-ink/25";
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-50">
      <span className={`${corner} top-3 left-3 border-t-2 border-l-2`} />
      <span className={`${corner} top-3 right-3 border-t-2 border-r-2`} />
      <span className={`${corner} bottom-3 left-3 border-b-2 border-l-2`} />
      <span className={`${corner} right-3 bottom-3 border-r-2 border-b-2`} />
    </div>
  );
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${barlow.variable} ${barlowCondensed.variable} h-full antialiased`}>
      <body className="min-h-full">
        {children}
        <CornerMarks />
      </body>
    </html>
  );
}
