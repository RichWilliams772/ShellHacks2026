// Hover/focus tooltip for technical terms. Uses the native title so it works with keyboard and screen readers.
export default function InfoTip({ text }: { text: string }) {
  return (
    <span
      tabIndex={0}
      title={text}
      aria-label={text}
      className="ml-1 inline-grid h-4 w-4 cursor-help place-items-center rounded-full border border-slate-300 text-[10px] font-semibold text-slate-500 align-middle"
    >
      i
    </span>
  );
}
