// Frontend-only display settings. Scoring weights live in the analysis pipeline, never here.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// true = use the bundled snapshot of real analysis output (lib/mock/analyze.json) instead of the backend.
// Set NEXT_PUBLIC_USE_MOCK=false in .env.local once POST /analyze works.
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== "false";

// MVP compares exactly these two (spec §3).
export const UTILITY_A = "Duke Energy Florida";
export const UTILITY_B = "Tampa Electric";

// Map/legend colors per utility; keep in sync with --color-duke / --color-teco in globals.css.
export const UTILITY_COLORS: Record<string, string> = {
  "Duke Energy Florida": "#2456b8",
  "Tampa Electric": "#e08a12",
};
export const FALLBACK_COLORS = ["#2456b8", "#e08a12", "#5b6472"];
export const REDLINE = "#c8352b";

export const MAP_CENTER: [number, number] = [28.6, -82.3]; // central Florida
export const MAP_ZOOM = 7;
