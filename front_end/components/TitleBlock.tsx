import type { AnalyzeSummary } from "@/lib/types";
import { UTILITY_A, UTILITY_B, USE_MOCK } from "@/lib/config";
import { utilityColor, utilityShape } from "@/lib/format";
import UtilityMarker from "./UtilityMarker";

interface Props {
  summary: AnalyzeSummary | null;
  analyzedAt: Date | null;
  loading: boolean;
  onAnalyze: () => void;
}

// The two utility shapes from UtilityMarker, overlapping - a coordination opportunity is
// literally where a Duke circle and a TECO diamond sit close together, so the mark drawing
// them on top of each other isn't decoration, it's the app's own idea in miniature. Multiply
// blending gives the overlap its own third tone instead of one shape just covering the other.
function BrandMark() {
  return (
    <svg width="34" height="34" viewBox="0 0 34 34" aria-hidden className="shrink-0">
      <circle cx="14" cy="17" r="9" fill="var(--color-duke)" style={{ mixBlendMode: "multiply" }} />
      <polygon points="24,8 33,17 24,26 15,17" fill="var(--color-teco)" style={{ mixBlendMode: "multiply" }} />
    </svg>
  );
}

// A soft tint of the utility's own color behind its name - the only color in the header
// besides the brand mark, and it is the same two colors the map already uses for these two
// utilities, not a new palette choice.
function UtilityChip({ name, color, shape }: { name: string; color: string; shape: ReturnType<typeof utilityShape> }) {
  return (
    <span
      className="flex items-center gap-2 rounded-full border px-3.5 py-1.5"
      style={{
        borderColor: `color-mix(in srgb, ${color} 40%, var(--color-rule))`,
        background: `color-mix(in srgb, ${color} 7%, var(--color-sheet))`,
      }}
    >
      <UtilityMarker shape={shape} color={color} size={12} />
      {name}
    </span>
  );
}

// Styled after the title block on an engineering drawing: what is being compared, and the result.
export default function TitleBlock({ summary, analyzedAt, loading, onAnalyze }: Props) {
  return (
    <header className="sticky top-0 z-30 border-b border-ink bg-sheet/90 shadow-[0_12px_28px_-18px_rgba(27,34,48,0.45)] backdrop-blur-md">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-end justify-between gap-x-8 gap-y-3 px-4 py-4 sm:px-6">
        <div className="flex items-center gap-3">
          <BrandMark />
          <div>
            <h1 className="font-display text-4xl leading-none font-bold">GridSync</h1>
            <p className="mt-1 text-graphite">Find where the grid can build together.</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <p className="flex flex-wrap items-center gap-x-3 font-display text-lg font-semibold">
            <UtilityChip name={UTILITY_A} color={utilityColor(UTILITY_A)} shape={utilityShape(UTILITY_A)} />
            <span className="text-graphite" aria-label="compared with">
              ⟷
            </span>
            <UtilityChip name={UTILITY_B} color={utilityColor(UTILITY_B)} shape={utilityShape(UTILITY_B)} />
          </p>
          <button
            type="button"
            onClick={onAnalyze}
            disabled={loading}
            className="flex items-center gap-2.5 rounded-lg bg-ink px-5 py-2.5 font-display text-lg font-semibold text-paper shadow-[0_2px_8px_-2px_rgba(27,34,48,0.4)] transition-shadow hover:bg-redline hover:shadow-[0_4px_14px_-2px_rgba(200,53,43,0.45)] disabled:cursor-wait disabled:opacity-70 disabled:hover:bg-ink disabled:hover:shadow-[0_2px_8px_-2px_rgba(27,34,48,0.4)]"
          >
            {loading && <span className="h-2 w-2 shrink-0 animate-pulse bg-paper motion-reduce:animate-none" aria-hidden />}
            {loading ? "Analyzing" : "Analyze projects"}
          </button>
        </div>
      </div>

      {summary && (
        <div className="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-x-4 gap-y-2 border-t border-rule px-4 py-2 sm:px-6">
          <p className="text-graphite">
            Checked <strong className="font-semibold text-ink">{summary.pairs_analyzed}</strong> project pairs across{" "}
            <strong className="font-semibold text-ink">{summary.projects_analyzed}</strong> projects.{" "}
            <strong className="font-semibold text-ink">{summary.eligible_opportunities}</strong> have enough data to score.
            {USE_MOCK && " Showing the saved analysis run."}
          </p>
          {analyzedAt && (
            <p className="flex shrink-0 divide-x divide-graphite border border-graphite text-xs font-semibold tracking-wide text-graphite uppercase">
              <span className="px-2 py-1">Reviewed</span>
              <span className="px-2 py-1 text-ink">
                {analyzedAt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
              </span>
            </p>
          )}
        </div>
      )}
    </header>
  );
}
