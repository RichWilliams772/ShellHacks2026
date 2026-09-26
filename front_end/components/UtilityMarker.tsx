import type { MarkerShape } from "@/lib/format";

// Small shape swatch used in legends and cards so utilities differ by shape, not just color.
export default function UtilityMarker({ shape, color, size = 10 }: { shape: MarkerShape; color: string; size?: number }) {
  const common = { width: size, height: size, background: color, display: "inline-block", flexShrink: 0 } as const;
  if (shape === "circle") return <span aria-hidden style={{ ...common, borderRadius: "9999px" }} />;
  if (shape === "diamond")
    return <span aria-hidden style={{ ...common, width: size * 0.8, height: size * 0.8, transform: "rotate(45deg)", margin: size * 0.1 }} />;
  return <span aria-hidden style={{ ...common, borderRadius: 2 }} />;
}
