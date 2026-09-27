// Shown while an analysis run is in flight. The four lines are the pipeline's own scoring
// dimensions (the same four the Score breakdown draws in OpportunityDetail.tsx), not an
// invented sequence - this is what "Analyzing…" is actually doing, made visible in order.
const DIMENSIONS = ["Geographic proximity", "Schedule alignment", "Project description similarity", "Infrastructure compatibility"];

export default function AnalysisProgress() {
  return (
    <div className="px-4 py-6" role="status" aria-label="Comparing project pairs">
      <p className="text-graphite">Comparing every Duke and TECO project pair on:</p>
      <ul className="mt-3 space-y-2.5">
        {DIMENSIONS.map((label, i) => (
          <li key={label} className="flex items-center gap-2.5 text-sm">
            <span className="stage-check h-3 w-3 shrink-0 border border-graphite" style={{ animationDelay: `${i * 260 + 100}ms` }} />
            <span>{label}</span>
          </li>
        ))}
      </ul>
      <div className="relative mt-5 h-[2px] overflow-hidden bg-rule">
        <span className="scan-sweep absolute inset-y-0 left-0 w-2/5 bg-redline" />
      </div>
    </div>
  );
}
