import { HIGH_OPPORTUNITY_SCORE } from "@/lib/config";

// Displays the backend's score. Color bands are purely visual.
export default function ScoreBadge({ score, size = "md" }: { score: number; size?: "md" | "lg" }) {
  const tone =
    score >= HIGH_OPPORTUNITY_SCORE
      ? "bg-emerald-50 text-emerald-800 border-emerald-300"
      : score >= 50
        ? "bg-amber-50 text-amber-800 border-amber-300"
        : "bg-slate-50 text-slate-700 border-slate-300";
  const sz = size === "lg" ? "px-4 py-2 text-2xl" : "px-2.5 py-1 text-sm";
  return (
    <span className={`inline-flex items-baseline gap-0.5 rounded-lg border font-semibold tabular-nums ${tone} ${sz}`}>
      {Math.round(score)}
      <span className="text-[0.7em] font-medium opacity-70">/100</span>
    </span>
  );
}
