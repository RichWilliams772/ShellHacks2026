// A calibrated dial, not a stat card: the Coordination Score read like an instrument
// gauge, with tick marks at the same 90-degree corner style as the map's dimension
// ticks (ProjectMap.tsx). No color bands - there is no validated threshold for a
// "high" opportunity (see ScoreBadge), so the fill is always ink, never redline or a
// traffic-light color, regardless of the value.
const START = -135; // degrees, 0 = top, clockwise
const SWEEP = 270;

function polar(cx: number, cy: number, r: number, deg: number) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)] as const;
}

function arcPath(cx: number, cy: number, r: number, fromDeg: number, toDeg: number) {
  const [x1, y1] = polar(cx, cy, r, fromDeg);
  const [x2, y2] = polar(cx, cy, r, toDeg);
  const large = toDeg - fromDeg > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
}

export default function ScoreGauge({ score, size = 108 }: { score: number; size?: number }) {
  const cx = 50;
  const cy = 54;
  const r = 40;
  const clamped = Math.min(100, Math.max(0, score));
  const valueEnd = START + (clamped / 100) * SWEEP;
  const ticks = [0, 25, 50, 75, 100];

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" width={size} height={size} role="img" aria-label={`Coordination score ${Math.round(score)} of 100`}>
        <path d={arcPath(cx, cy, r, START, START + SWEEP)} fill="none" stroke="var(--color-rule)" strokeWidth={5} />
        {clamped > 0 && (
          <path d={arcPath(cx, cy, r, START, valueEnd)} fill="none" stroke="var(--color-ink)" strokeWidth={5} strokeLinecap="butt" />
        )}
        {ticks.map((t) => {
          const deg = START + (t / 100) * SWEEP;
          const [ix, iy] = polar(cx, cy, r - 5, deg);
          const [ox, oy] = polar(cx, cy, r + 5, deg);
          return <line key={t} x1={ix} y1={iy} x2={ox} y2={oy} stroke="var(--color-graphite)" strokeWidth={1} />;
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center pt-2">
        <span className="font-display text-3xl leading-none font-semibold">{Math.round(score)}</span>
        <span className="text-[11px] text-graphite">/ 100</span>
      </div>
    </div>
  );
}
