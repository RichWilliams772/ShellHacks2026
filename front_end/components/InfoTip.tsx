// Hover/focus tooltip for technical terms. Uses the native title so it works with keyboard and screen readers.
export default function InfoTip({ text }: { text: string }) {
  return (
    <span
      tabIndex={0}
      title={text}
      aria-label={text}
      className="ml-1 inline-grid h-4 w-4 cursor-help place-items-center rounded-full border border-graphite align-middle text-[10px] font-semibold text-graphite"
    >
      ?
    </span>
  );
}
