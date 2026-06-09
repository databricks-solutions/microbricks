/**
 * Timeline of recent API calls.
 *
 * Each call is rendered as a single dot at (elapsed_time, latency). Color
 * encodes the backend service (matching the StatsPanel legend); failures get
 * a red ring so they stand out against the otherwise per-service color.
 *
 * The chart auto-scales:
 *   - X axis: a sliding window of the last `windowMs` (default 30s)
 *   - Y axis: 0 → max(observed latency in window, MIN_Y_MAX), with a sqrt
 *     scale so a few outliers don't flatten the rest of the data.
 *
 * Why SVG and not a chart library: we draw ≤ 600 dots, no axes interaction,
 * and we want zero extra deps. A 60-line SVG is plenty.
 */
import { useMemo } from "react";

import type { CallSample } from "./stats-panel";

interface TimelinePanelProps {
  samples: CallSample[];
  /** Width of the rolling window in ms. */
  windowMs?: number;
}

/** Same emoji + label table the StatsPanel uses. Kept here to avoid imports across components. */
const SERVICE_META: Record<string, { label: string; color: string }> = {
  patient:      { label: "patient",      color: "#2563eb" },
  appointment:  { label: "appointment",  color: "#f59e0b" },
  lab:          { label: "lab",          color: "#8b5cf6" },
  prescription: { label: "prescription", color: "#ec4899" },
  billing:      { label: "billing",      color: "#14b8a6" },
  provider:     { label: "provider",     color: "#10b981" },
};

const FALLBACK_COLOR = "#64748b";
const MIN_Y_MAX = 250; // ms — keep the y-axis from collapsing on a quiet run.
const CHART_HEIGHT = 200;
const PAD_TOP = 14;
const PAD_BOTTOM = 24;
const PAD_LEFT = 36;
const PAD_RIGHT = 8;

/** sqrt-scaled y so 1ms ↔ 50ms ↔ 1000ms are all visible. */
function yScale(latencyMs: number, yMax: number, innerH: number) {
  const t = Math.sqrt(Math.max(0, latencyMs)) / Math.sqrt(Math.max(1, yMax));
  return innerH - t * innerH;
}

function niceTicks(maxMs: number): number[] {
  // Pick a few round latency lines that span [0, maxMs].
  if (maxMs <= 100) return [0, 25, 50, 75, 100];
  if (maxMs <= 250) return [0, 50, 100, 150, 200, 250];
  if (maxMs <= 500) return [0, 100, 250, 500];
  if (maxMs <= 1000) return [0, 100, 250, 500, 1000];
  if (maxMs <= 2500) return [0, 250, 500, 1000, 2500];
  return [0, 500, 1000, 2500, 5000];
}

export function TimelinePanel({ samples, windowMs = 30_000 }: TimelinePanelProps) {
  const { points, xMin, xMax, yMax, services } = useMemo(() => {
    if (samples.length === 0) {
      return { points: [] as CallSample[], xMin: 0, xMax: windowMs, yMax: MIN_Y_MAX, services: [] as string[] };
    }
    const latest = samples[samples.length - 1]!.t;
    const lower = Math.max(0, latest - windowMs);
    const filtered = samples.filter((s) => s.t >= lower);
    let observedMax = MIN_Y_MAX;
    const seenServices = new Set<string>();
    for (const s of filtered) {
      if (s.latencyMs > observedMax) observedMax = s.latencyMs;
      seenServices.add(s.service);
    }
    // Round yMax up to the next nice tick boundary so the axis labels line up.
    const ticks = niceTicks(observedMax);
    const ceil = ticks[ticks.length - 1] ?? observedMax;
    return {
      points: filtered,
      xMin: lower,
      xMax: lower + windowMs,
      yMax: ceil,
      services: Array.from(seenServices).sort(),
    };
  }, [samples, windowMs]);

  const width = 760; // SVG draws into a viewBox; CSS scales it to container width.
  const innerW = width - PAD_LEFT - PAD_RIGHT;
  const innerH = CHART_HEIGHT - PAD_TOP - PAD_BOTTOM;
  const xRange = Math.max(1, xMax - xMin);
  const yTicks = niceTicks(yMax);

  return (
    <div className="rounded-2xl border border-border bg-card p-4">
      <div className="flex items-baseline justify-between mb-3 gap-3 flex-wrap">
        <div>
          <h3 className="text-sm font-medium">API call timeline</h3>
          <p className="text-[11px] text-muted-foreground">
            Last {Math.round(windowMs / 1000)}s · each dot is one backend call ·
            y = latency · failures circled in red
          </p>
        </div>
        <Legend services={services} />
      </div>

      <div className="w-full overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${CHART_HEIGHT}`}
          width="100%"
          height={CHART_HEIGHT}
          preserveAspectRatio="none"
          role="img"
          aria-label="API call latency timeline"
        >
          {/* Y axis grid + labels */}
          {yTicks.map((tick) => {
            const y = PAD_TOP + yScale(tick, yMax, innerH);
            return (
              <g key={tick}>
                <line
                  x1={PAD_LEFT}
                  x2={width - PAD_RIGHT}
                  y1={y}
                  y2={y}
                  stroke="oklch(0.92 0.005 240)"
                  strokeDasharray={tick === 0 ? undefined : "2 3"}
                />
                <text
                  x={PAD_LEFT - 4}
                  y={y + 3}
                  textAnchor="end"
                  className="fill-muted-foreground"
                  fontSize="9"
                >
                  {tick}ms
                </text>
              </g>
            );
          })}

          {/* X axis labels — show start / mid / end of the window */}
          {[0, 0.5, 1].map((frac) => {
            const tMs = xMin + xRange * frac;
            const x = PAD_LEFT + frac * innerW;
            return (
              <text
                key={frac}
                x={x}
                y={CHART_HEIGHT - 6}
                textAnchor={frac === 0 ? "start" : frac === 1 ? "end" : "middle"}
                className="fill-muted-foreground"
                fontSize="9"
              >
                {(tMs / 1000).toFixed(1)}s
              </text>
            );
          })}

          {/* Data points */}
          {points.length === 0 ? (
            <text
              x={width / 2}
              y={CHART_HEIGHT / 2}
              textAnchor="middle"
              className="fill-muted-foreground"
              fontSize="11"
            >
              No calls yet — start the simulator to see the timeline.
            </text>
          ) : (
            points.map((p, i) => {
              const fx = (p.t - xMin) / xRange;
              const cx = PAD_LEFT + fx * innerW;
              const cy = PAD_TOP + yScale(p.latencyMs, yMax, innerH);
              const color = SERVICE_META[p.service]?.color ?? FALLBACK_COLOR;
              return (
                <circle
                  key={`${p.t}-${i}`}
                  cx={cx}
                  cy={cy}
                  r={p.ok ? 2.8 : 3.4}
                  fill={color}
                  fillOpacity={0.75}
                  stroke={p.ok ? "white" : "#dc2626"}
                  strokeWidth={p.ok ? 0.6 : 1.4}
                >
                  <title>
                    {p.service}.{p.op} — {p.latencyMs}ms
                    {!p.ok ? " (failed)" : ""}
                  </title>
                </circle>
              );
            })
          )}
        </svg>
      </div>
    </div>
  );
}

function Legend({ services }: { services: string[] }) {
  if (services.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px]">
      {services.map((svc) => {
        const meta = SERVICE_META[svc];
        const color = meta?.color ?? FALLBACK_COLOR;
        return (
          <span key={svc} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: color }}
            />
            <span className="text-muted-foreground">{meta?.label ?? svc}</span>
          </span>
        );
      })}
    </div>
  );
}
