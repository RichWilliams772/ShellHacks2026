export default function Header({ demo }: { demo: boolean }) {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-slate-900 text-lg font-bold text-amber-400">
            ⚡
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-slate-900">GridSync</h1>
            <p className="text-sm text-slate-500">
              Find where the grid can build together.{" "}
              <span className="hidden text-slate-400 sm:inline">· Infrastructure coordination intelligence</span>
            </p>
          </div>
        </div>
        {demo && (
          <span
            className="rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800"
            title="Synthetic records for UI development. Not real utility projects."
          >
            DEMO DATA — not real utility records
          </span>
        )}
      </div>
    </header>
  );
}
