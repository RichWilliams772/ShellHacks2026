import type { AnalyzeSummary } from "@/lib/types";
import { UTILITY_A, UTILITY_B, USE_MOCK } from "@/lib/config";
import { utilityColor, utilityShape } from "@/lib/format";
import UtilityMarker from "./UtilityMarker";

interface Props {
  summary: AnalyzeSummary | null;
  loading: boolean;
  onAnalyze: () => void;
}

// Styled after the title block on an engineering drawing: what is being compared, and the result.
export default function TitleBlock({ summary, loading, onAnalyze }: Props) {
  return (
    <header className="gs-network border-b border-rule pt-[env(safe-area-inset-top)]">
      <div className="mx-auto flex max-w-[1500px] flex-col items-stretch gap-3 px-4 py-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between sm:gap-x-8 sm:px-6 sm:py-4">
        <div className="min-w-0">
          <h1 className="font-display text-3xl leading-none font-bold tracking-tight sm:text-4xl">GridSync</h1>
          <p className="mt-1 text-graphite">See the overlap. Build the grid together.</p>
        </div>

        <div className="flex min-w-0 flex-col items-stretch gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-6">
          <p className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 font-display text-lg font-semibold break-words sm:text-xl">
            <span className="flex min-w-0 items-center gap-2">
              <UtilityMarker shape={utilityShape(UTILITY_A)} color={utilityColor(UTILITY_A)} size={12} />
              <span className="min-w-0 break-words">{UTILITY_A}</span>
            </span>
            <span className="text-graphite" aria-label="compared with">
              ⟷
            </span>
            <span className="flex min-w-0 items-center gap-2">
              <UtilityMarker shape={utilityShape(UTILITY_B)} color={utilityColor(UTILITY_B)} size={12} />
              <span className="min-w-0 break-words">{UTILITY_B}</span>
            </span>
          </p>
          <button
            type="button"
            onClick={onAnalyze}
            disabled={loading}
            className="min-h-11 w-full rounded-full bg-ink px-5 py-2.5 font-display text-lg font-semibold text-paper hover:bg-cyan hover:text-paper disabled:cursor-wait disabled:opacity-60 sm:min-h-0 sm:w-auto"
          >
            {loading ? "Analyzing…" : "Analyze projects"}
          </button>
        </div>
      </div>

      {summary && (
        <p className="mx-auto max-w-[1500px] border-t border-rule px-4 py-2 text-graphite sm:px-6">
          Checked <strong className="font-semibold text-ink">{summary.pairs_analyzed}</strong> project pairs across{" "}
          <strong className="font-semibold text-ink">{summary.projects_analyzed}</strong> projects.{" "}
          <strong className="font-semibold text-ink">{summary.eligible_opportunities}</strong> have enough data to score.
          {USE_MOCK && " Showing the saved analysis run."}
        </p>
      )}
    </header>
  );
}
