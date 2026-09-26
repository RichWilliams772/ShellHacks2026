// Frontend-only display settings. Scoring weights live in the backend config, never here.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// true = use the bundled demo dataset instead of calling the backend.
// Set NEXT_PUBLIC_USE_MOCK=false in .env.local once POST /analyze works.
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== "false";

// Only used for the score badge color (green at or above this). It does not change any number.
export const HIGH_OPPORTUNITY_SCORE = 75;

export const DEFAULT_UTILITY_A = "Duke Energy Florida";
export const DEFAULT_UTILITY_B = "Tampa Electric";

// Colors per utility on the map and in badges. Unknown utilities fall back to the last entry.
export const UTILITY_COLORS: Record<string, string> = {
  "Duke Energy Florida": "#2563eb",
  "Tampa Electric": "#ea580c",
};
export const FALLBACK_COLORS = ["#2563eb", "#ea580c", "#7c3aed", "#0d9488"];

export const MAP_CENTER: [number, number] = [28.0, -82.4]; // Tampa Bay
export const MAP_ZOOM = 8;
