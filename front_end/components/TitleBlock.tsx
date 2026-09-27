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
    <header className="border-b border-ink bg-sheet">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-end justify-between gap-x-8 gap-y-3 px-4 py-4 sm:px-6">
        <div>
          <h1 className="font-display text-4xl leading-none font-bold">GridSync</h1>
          <p className="mt-1 text-graphite">Find where the grid can build together.</p>
        </div>

        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <p className="flex flex-wrap items-center gap-x-3 font-display text-xl font-semibold">
            <span className="flex items-center gap-2">
              <UtilityMarker shape={utilityShape(UTILITY_A)} color={utilityColor(UTILITY_A)} size={12} />
              {UTILITY_A}
            </span>
            <span className="text-graphite" aria-label="compared with">
              ⟷
            </span>
            <span className="flex items-center gap-2">
              <UtilityMarker shape={utilityShape(UTILITY_B)} color={utilityColor(UTILITY_B)} size={12} />
              {UTILITY_B}
            </span>
          </p>
          <button
            type="button"
            onClick={onAnalyze}
            disabled={loading}
            className="rounded-sm bg-ink px-5 py-2.5 font-display text-lg font-semibold text-paper hover:bg-redline disabled:cursor-wait disabled:opacity-60"
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
