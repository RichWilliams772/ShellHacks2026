// Displays the pipeline's Coordination Score as-is (rounded for display). No color bands:
// there is no validated threshold for a "high" opportunity, so the number speaks for itself.
export default function ScoreBadge({ score, size = "md" }: { score: number; size?: "md" | "lg" }) {
  const sz = size === "lg" ? "text-5xl" : "text-2xl";
  return (
    <span className={`font-display leading-none font-semibold ${sz}`}>
      {Math.round(score)}
      <span className="text-[0.45em] font-medium text-graphite">/100</span>
    </span>
  );
}
