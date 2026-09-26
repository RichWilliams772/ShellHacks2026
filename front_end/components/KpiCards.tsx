interface Props {
  projectsAnalyzed: number | null;
  opportunities: number | null;
  highestScore: number | null;
  utilitiesCompared: number | null;
  loading: boolean;
}

function Card({ label, value, suffix, loading }: { label: string; value: number | null; suffix?: string; loading: boolean }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      {loading ? (
        <div className="mt-2 h-8 w-16 animate-pulse rounded bg-slate-200" />
      ) : (
        <p className="mt-1 text-3xl font-semibold tabular-nums text-slate-900">
          {value ?? "—"}
          {value != null && suffix && <span className="text-base font-medium text-slate-400">{suffix}</span>}
        </p>
      )}
    </div>
  );
}

export default function KpiCards(p: Props) {
  return (
    <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Card label="Projects analyzed" value={p.projectsAnalyzed} loading={p.loading} />
      <Card label="Coordination opportunities" value={p.opportunities} loading={p.loading} />
      <Card label="Highest coordination score" value={p.highestScore} suffix="/100" loading={p.loading} />
      <Card label="Utilities compared" value={p.utilitiesCompared} loading={p.loading} />
    </section>
  );
}
