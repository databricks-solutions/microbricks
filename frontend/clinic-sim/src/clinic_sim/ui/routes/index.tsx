/**
 * Simulator page — the only route. Owns the run state and aggregates events.
 *
 * Why state is here and not in a hook: the parent owns both the EventSource
 * lifetime and the derived stats, so co-locating them keeps the cleanup
 * deterministic. The event handler updates two slices (in-flight patient
 * map + aggregate stats) in a single tick to keep them in sync.
 */
import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ClinicFloor, type ActivePatient } from "@/components/clinic-floor";
import { ControlPanel, type SimStatus } from "@/components/control-panel";
import {
  StatsPanel,
  type CallSample,
  type PerServiceStats,
  type SimStats,
} from "@/components/stats-panel";
import { TimelinePanel } from "@/components/timeline-panel";
import { openSimStream, type SimEvent, type Stage } from "@/lib/stream";

export const Route = createFileRoute("/")({
  component: SimulatorPage,
});

const EMPTY_STAGE_COUNTS: Record<Stage, number> = {
  entering: 0,
  reception: 0,
  waiting: 0,
  exam: 0,
  lab: 0,
  pharmacy: 0,
  checkout: 0,
  leaving: 0,
  done: 0,
  failed: 0,
};

const EMPTY_STATS: SimStats = {
  total: 0,
  inFlight: 0,
  done: 0,
  failed: 0,
  byStage: { ...EMPTY_STAGE_COUNTS },
  byService: {},
  totalCalls: 0,
  callsOk: 0,
  callsFailed: 0,
  callsPerSecond: 0,
  totalLatencyMs: 0,
  avgLatencyMs: 0,
  recent: [],
  timeline: [],
};

const RECENT_CAP = 60;
// Cap visible avatars; everything else still counts in stats but isn't drawn.
// This is a *sticky* cap — once a patient is in the visible set they keep
// their slot until they finish, so they don't pop in and out as newer
// patients arrive. New patients only become visible when a slot opens up.
const VISIBLE_AVATAR_CAP = 100;
// Sliding chart window for the timeline panel. Any call with `elapsed_ms`
// inside [latest - TIMELINE_WINDOW_MS, latest] is rendered as a dot.
const TIMELINE_WINDOW_MS = 30_000;
// Hard cap on retained samples as a safety net. With a 30s window we
// expect well under this in normal runs; the cap only kicks in for
// pathological per-second rates.
const TIMELINE_CAP = 8000;

function SimulatorPage() {
  const [count, setCount] = useState(50);
  const [registerProb, setRegisterProb] = useState(0.3);
  const [labProb, setLabProb] = useState(0.4);
  const [rxProb, setRxProb] = useState(0.5);
  const [maxConc, setMaxConc] = useState(16);
  const [spacingMs, setSpacingMs] = useState(80);

  const [status, setStatus] = useState<SimStatus>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Active patient map: journey_id → ActivePatient (only "alive" patients,
  // i.e. not yet done/failed/leaving).
  const [activePatients, setActivePatients] = useState<
    Record<number, ActivePatient>
  >({});
  // Sticky set of journey_ids that currently "own" an on-screen slot.
  // Updated in lockstep with `activePatients` from `flushPending` so
  // visibility is deterministic relative to incoming events.
  const [visibleIds, setVisibleIds] = useState<number[]>([]);
  const [stats, setStats] = useState<SimStats>(EMPTY_STATS);

  const cancelRef = useRef<(() => void) | null>(null);
  // Buffer incoming events; we drain on a rAF tick so 10k+ events don't
  // each trigger a React re-render.
  const pendingRef = useRef<SimEvent[]>([]);
  const rafRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(0);
  // Authoritative copies of the two slices we need to recompute the
  // sticky visible set inside `flushPending`. State setters are async, so
  // we keep refs in lockstep.
  const activeRef = useRef<Record<number, ActivePatient>>({});
  const visibleRef = useRef<number[]>([]);

  const flushPending = useCallback(() => {
    rafRef.current = null;
    const batch = pendingRef.current;
    if (batch.length === 0) return;
    pendingRef.current = [];

    // 1. Apply the batch to the active-patient map.
    const nextActive: Record<number, ActivePatient> = { ...activeRef.current };
    for (const ev of batch) {
      if (ev.stage === "done" || ev.stage === "failed" || ev.stage === "leaving") {
        delete nextActive[ev.journey_id];
      } else {
        nextActive[ev.journey_id] = {
          journey_id: ev.journey_id,
          patient_name: ev.patient_name,
          stage: ev.stage,
          patient_id: ev.patient_id ?? null,
        };
      }
    }
    activeRef.current = nextActive;
    setActivePatients(nextActive);

    // 2. Update the sticky visible set: keep every previously-visible id
    //    that's still active, then fill empty slots with the *oldest*
    //    not-yet-visible active patients. Oldest-first means slots are
    //    filled by patients who entered earlier and will likely finish
    //    sooner, freeing the slot back up at a steady rate.
    const prevVisible = visibleRef.current;
    const kept: number[] = [];
    const keptSet = new Set<number>();
    for (const id of prevVisible) {
      if (nextActive[id] !== undefined) {
        kept.push(id);
        keptSet.add(id);
      }
    }
    if (kept.length < VISIBLE_AVATAR_CAP) {
      const candidates: number[] = [];
      for (const idStr in nextActive) {
        const id = Number(idStr);
        if (!keptSet.has(id)) candidates.push(id);
      }
      candidates.sort((a, b) => a - b);
      for (const id of candidates) {
        if (kept.length >= VISIBLE_AVATAR_CAP) break;
        kept.push(id);
      }
    }
    // Avoid pointless re-renders when nothing actually changed.
    const changed =
      kept.length !== prevVisible.length ||
      kept.some((id, i) => id !== prevVisible[i]);
    if (changed) {
      visibleRef.current = kept;
      setVisibleIds(kept);
    }

    setStats((prev) => {
      const byStage = { ...prev.byStage };
      const byService = { ...prev.byService };
      let totalCalls = prev.totalCalls;
      let callsOk = prev.callsOk;
      let callsFailed = prev.callsFailed;
      let totalLatencyMs = prev.totalLatencyMs;
      let done = prev.done;
      let failed = prev.failed;
      let total = prev.total;
      const newSamples: CallSample[] = [];

      for (const ev of batch) {
        if (ev.stage === "entering") total++;
        if (ev.stage === "done") done++;
        if (ev.stage === "failed") failed++;
        byStage[ev.stage] = (byStage[ev.stage] ?? 0) + 1;

        if (ev.service && ev.op) {
          totalCalls++;
          const wasOk = !ev.error
            && (ev.status_code == null || ev.status_code < 400);
          if (wasOk) callsOk++; else callsFailed++;
          totalLatencyMs += ev.latency_ms ?? 0;
          const cur: PerServiceStats = byService[ev.service]
            ? { ...byService[ev.service] }
            : { service: ev.service, total: 0, ok: 0, failed: 0, latencySumMs: 0, ops: {} };
          cur.total++;
          if (wasOk) cur.ok++; else cur.failed++;
          cur.latencySumMs += ev.latency_ms ?? 0;
          cur.ops = { ...cur.ops, [ev.op]: (cur.ops[ev.op] ?? 0) + 1 };
          byService[ev.service] = cur;

          newSamples.push({
            t: ev.elapsed_ms,
            service: ev.service,
            op: ev.op,
            latencyMs: ev.latency_ms ?? 0,
            ok: wasOk,
          });
        }
      }

      const recent = [...prev.recent, ...batch].slice(-RECENT_CAP);
      // Timeline retention is window-based, not just count-based: we keep
      // *every* call whose t is inside the chart's sliding window. The
      // count cap is just a guard against unbounded growth.
      let timeline: CallSample[];
      if (newSamples.length === 0) {
        timeline = prev.timeline;
      } else {
        const latestT = newSamples[newSamples.length - 1]!.t;
        const cutoff = latestT - TIMELINE_WINDOW_MS;
        const merged = [...prev.timeline, ...newSamples];
        // Slice off anything that fell out of the window; both arrays are
        // monotonic in `t` so a simple index walk would also work, but a
        // .filter is plenty for our buffer sizes.
        const filtered = merged.filter((s) => s.t >= cutoff);
        timeline = filtered.length > TIMELINE_CAP
          ? filtered.slice(-TIMELINE_CAP)
          : filtered;
      }
      const elapsedSec = Math.max(0.001, (performance.now() - startTimeRef.current) / 1000);
      const callsPerSecond = totalCalls / elapsedSec;
      const avgLatencyMs = totalCalls > 0 ? Math.round(totalLatencyMs / totalCalls) : 0;
      const inFlight = total - done - failed;

      return {
        total,
        inFlight,
        done,
        failed,
        byStage,
        byService,
        totalCalls,
        callsOk,
        callsFailed,
        callsPerSecond,
        totalLatencyMs,
        avgLatencyMs,
        recent,
        timeline,
      };
    });
  }, []);

  const onEvent = useCallback(
    (ev: SimEvent) => {
      pendingRef.current.push(ev);
      if (rafRef.current == null) {
        rafRef.current = requestAnimationFrame(flushPending);
      }
    },
    [flushPending],
  );

  const handleStart = useCallback(() => {
    setErrorMsg(null);
    setStatus("running");
    setActivePatients({});
    setVisibleIds([]);
    setStats(EMPTY_STATS);
    activeRef.current = {};
    visibleRef.current = [];
    pendingRef.current = [];
    startTimeRef.current = performance.now();

    cancelRef.current = openSimStream(
      {
        count,
        register_probability: registerProb,
        lab_probability: labProb,
        rx_probability: rxProb,
        max_concurrency: maxConc,
        journey_spacing_ms: spacingMs,
      },
      onEvent,
      () => {
        flushPending();
        setStatus("completed");
        cancelRef.current = null;
      },
      (msg) => {
        flushPending();
        setErrorMsg(msg);
        setStatus("error");
        cancelRef.current = null;
      },
    );
  }, [count, registerProb, labProb, rxProb, maxConc, spacingMs, onEvent, flushPending]);

  const handleStop = useCallback(() => {
    cancelRef.current?.();
    cancelRef.current = null;
    setStatus("idle");
  }, []);

  const handleReset = useCallback(() => {
    setActivePatients({});
    setVisibleIds([]);
    setStats(EMPTY_STATS);
    setErrorMsg(null);
    setStatus("idle");
    activeRef.current = {};
    visibleRef.current = [];
    pendingRef.current = [];
  }, []);

  // Clean up on unmount.
  useEffect(() => {
    return () => {
      cancelRef.current?.();
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // Materialize the sticky visible set into a list of patients. The set
  // is already capped at VISIBLE_AVATAR_CAP in `flushPending`, so this
  // is just a lookup. Patients that have already finished (no longer in
  // `activePatients`) are dropped here — the floor's AnimatePresence
  // will run their exit transition on the next render.
  const visiblePatients = useMemo(() => {
    const out: ActivePatient[] = [];
    for (const id of visibleIds) {
      const p = activePatients[id];
      if (p) out.push(p);
    }
    return out;
  }, [activePatients, visibleIds]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Patient flow simulator</h1>
        <p className="text-sm text-muted-foreground mt-1 max-w-3xl">
          Spawn synthetic patient visits that move through the clinic — reception,
          waiting, exam, lab, pharmacy, checkout — by making real CRUD calls
          against every backend service. Each avatar below corresponds to a live
          journey running on the BFF.
        </p>
      </div>

      <ControlPanel
        count={count}
        setCount={setCount}
        registerProbability={registerProb}
        setRegisterProbability={setRegisterProb}
        labProbability={labProb}
        setLabProbability={setLabProb}
        rxProbability={rxProb}
        setRxProbability={setRxProb}
        maxConcurrency={maxConc}
        setMaxConcurrency={setMaxConc}
        spacingMs={spacingMs}
        setSpacingMs={setSpacingMs}
        status={status}
        errorMsg={errorMsg}
        onStart={handleStart}
        onStop={handleStop}
        onReset={handleReset}
      />

      <ClinicFloor patients={visiblePatients} />

      <TimelinePanel samples={stats.timeline} />

      <StatsPanel stats={stats} requested={count} />
    </div>
  );
}
