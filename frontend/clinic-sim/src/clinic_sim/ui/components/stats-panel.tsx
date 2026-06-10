/**
 * Live stats: aggregate counters + per-service call breakdown + per-stage
 * histogram + recent calls strip.
 */
import { useMemo } from "react";

import type { Stage, SimEvent } from "@/lib/stream";

export interface PerServiceStats {
  service: string;
  total: number;
  ok: number;
  failed: number;
  latencySumMs: number;
  ops: Record<string, number>;
}

/**
 * One sampled API call, ready to plot on the timeline chart. We keep these
 * separate from `recent` (which is a scrolling text feed) so the chart can
 * use a different cap and a leaner shape.
 */
export interface CallSample {
  /** Stable unique id for React keying. */
  id: number;
  /** Elapsed ms since the run started — the X coordinate. */
  t: number;
  service: string;
  op: string;
  /** Server-reported call latency in ms — the Y coordinate. */
  latencyMs: number;
  /** false when the call returned a 4xx/5xx or threw. */
  ok: boolean;
}

export interface SimStats {
  total: number;
  inFlight: number;
  done: number;
  failed: number;
  byStage: Record<Stage, number>;
  byService: Record<string, PerServiceStats>;
  totalCalls: number;
  callsOk: number;
  callsFailed: number;
  callsPerSecond: number;
  totalLatencyMs: number;
  avgLatencyMs: number;
  recent: SimEvent[];
  /** Sliding window of recent API calls for the timeline chart. */
  timeline: CallSample[];
}

const SERVICE_LABELS: Record<string, { label: string; emoji: string }> = {
  patient: { label: "patient", emoji: "🪪" },
  appointment: { label: "appointment", emoji: "📅" },
  lab: { label: "lab", emoji: "🧪" },
  prescription: { label: "prescription", emoji: "💊" },
  billing: { label: "billing", emoji: "🧾" },
  provider: { label: "provider", emoji: "👨‍⚕️" },
};

interface StatsPanelProps {
  stats: SimStats;
  requested: number;
}

export function StatsPanel({ stats, requested }: StatsPanelProps) {
  const pct = requested > 0
    ? Math.min(100, Math.round(((stats.done + stats.failed) / requested) * 100))
    : 0;

  const services = useMemo(
    () =>
      Object.values(stats.byService).sort((a, b) => b.total - a.total),
    [stats.byService],
  );

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <BigStat
          label="Done"
          value={stats.done}
          accent="text-emerald-700"
          sub={`of ${requested.toLocaleString()} requested`}
        />
        <BigStat
          label="In flight"
          value={stats.inFlight}
          accent="text-sky-700"
        />
        <BigStat
          label="Failed"
          value={stats.failed}
          accent="text-red-700"
        />
        <BigStat
          label="Calls/sec"
          value={Math.round(stats.callsPerSecond)}
          accent="text-violet-700"
          sub={`${stats.totalCalls.toLocaleString()} total · avg ${stats.avgLatencyMs}ms`}
        />
      </div>

      <div className="rounded-2xl border border-border bg-card p-4">
        <div className="flex items-center justify-between mb-1.5">
          <h3 className="text-sm font-medium">Run progress</h3>
          <span className="text-xs tabular-nums text-muted-foreground">{pct}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
          <div
            className="h-full bg-primary transition-all duration-200"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <div className="rounded-2xl border border-border bg-card p-4">
        <h3 className="text-sm font-medium mb-3">Per-service calls</h3>
        {services.length === 0 ? (
          <p className="text-xs text-muted-foreground">No calls yet.</p>
        ) : (
          <div className="space-y-2">
            {services.map((svc) => {
              const meta = SERVICE_LABELS[svc.service] ?? { label: svc.service, emoji: "•" };
              const avg = svc.total > 0
                ? Math.round(svc.latencySumMs / svc.total)
                : 0;
              const errPct = svc.total > 0
                ? Math.round((svc.failed / svc.total) * 100)
                : 0;
              return (
                <div key={svc.service} className="flex items-center gap-3 text-sm">
                  <span className="text-base" aria-hidden>{meta.emoji}</span>
                  <span className="font-medium w-28">{meta.label}</span>
                  <span className="tabular-nums w-14 text-right text-foreground">
                    {svc.total.toLocaleString()}
                  </span>
                  <span className="tabular-nums w-16 text-right text-muted-foreground text-xs">
                    {avg}ms avg
                  </span>
                  <span
                    className={`tabular-nums w-12 text-right text-xs ${
                      errPct > 0 ? "text-red-700 font-medium" : "text-muted-foreground"
                    }`}
                  >
                    {errPct}% err
                  </span>
                  <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-primary"
                      style={{ width: `${Math.min(100, (svc.total / Math.max(1, stats.totalCalls)) * 100)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-border bg-card p-4">
        <h3 className="text-sm font-medium mb-3">Recent calls</h3>
        <div className="max-h-56 overflow-y-auto text-xs font-mono">
          {stats.recent.length === 0 ? (
            <p className="text-muted-foreground font-sans">No events yet.</p>
          ) : (
            <ul className="space-y-1">
              {stats.recent.slice().reverse().map((e, i) => (
                <li
                  key={`${e.journey_id}-${i}`}
                  className="flex items-center gap-2 whitespace-nowrap"
                >
                  <span className="tabular-nums text-muted-foreground w-14">
                    {(e.elapsed_ms / 1000).toFixed(2)}s
                  </span>
                  <span
                    className={`w-10 text-right tabular-nums ${
                      e.error || (e.status_code && e.status_code >= 400)
                        ? "text-red-700"
                        : e.latency_ms != null && e.latency_ms > 500
                        ? "text-amber-700"
                        : "text-emerald-700"
                    }`}
                  >
                    {e.latency_ms ?? "—"}ms
                  </span>
                  <span className="text-muted-foreground">#{e.journey_id}</span>
                  <span className="truncate">
                    {e.service ? `${e.service}: ` : ""}
                    {e.op ?? e.stage}
                  </span>
                  {e.error && (
                    <span className="text-red-700 truncate">— {e.error}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function BigStat(props: {
  label: string;
  value: number;
  accent?: string;
  sub?: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-card p-4 flex flex-col justify-between">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {props.label}
      </div>
      <div className={`text-2xl font-bold tabular-nums mt-1 ${props.accent ?? ""}`}>
        {props.value.toLocaleString()}
      </div>
      {props.sub && (
        <div className="text-[11px] text-muted-foreground mt-1">{props.sub}</div>
      )}
    </div>
  );
}
