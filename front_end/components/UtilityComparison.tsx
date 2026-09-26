"use client";

import { utilityColor } from "@/lib/format";

interface Props {
  utilities: string[];
  utilityA: string;
  utilityB: string;
  onChangeA: (v: string) => void;
  onChangeB: (v: string) => void;
  onAnalyze: () => void;
  loading: boolean;
}

function UtilitySelect({
  value,
  onChange,
  options,
  label,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  label: string;
}) {
  return (
    <label className="flex min-w-0 flex-1 items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2">
      <span className="h-3 w-3 shrink-0 rounded-full" style={{ background: utilityColor(value) }} />
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="min-w-0 flex-1 bg-transparent text-sm font-medium text-slate-900 outline-none"
      >
        {options.map((u) => (
          <option key={u} value={u}>
            {u}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function UtilityComparison(p: Props) {
  const same = p.utilityA === p.utilityB;
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center">
        <UtilitySelect label="Utility A" value={p.utilityA} onChange={p.onChangeA} options={p.utilities} />
        <button
          type="button"
          onClick={() => {
            p.onChangeA(p.utilityB);
            p.onChangeB(p.utilityA);
          }}
          className="self-center rounded-full border border-slate-300 px-3 py-1 text-slate-500 hover:bg-slate-50"
          aria-label="Swap utilities"
          title="Swap utilities"
        >
          ⇅
        </button>
        <UtilitySelect label="Utility B" value={p.utilityB} onChange={p.onChangeB} options={p.utilities} />
        <button
          type="button"
          onClick={p.onAnalyze}
          disabled={p.loading || same}
          className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {p.loading ? "Analyzing…" : "Analyze Opportunities"}
        </button>
      </div>
      {same && <p className="mt-2 text-sm text-red-600">Pick two different utilities to compare.</p>}
    </section>
  );
}
