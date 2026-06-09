/**
 * Control panel: count slider + probability sliders + start/stop buttons.
 * All inputs are kept in the parent's state — this component is purely
 * presentational.
 */
import { Play, Pause, RotateCcw } from "lucide-react";

import { cn } from "@/lib/utils";

export type SimStatus = "idle" | "running" | "completed" | "error";

interface ControlPanelProps {
  count: number;
  setCount: (n: number) => void;
  registerProbability: number;
  setRegisterProbability: (n: number) => void;
  labProbability: number;
  setLabProbability: (n: number) => void;
  rxProbability: number;
  setRxProbability: (n: number) => void;
  maxConcurrency: number;
  setMaxConcurrency: (n: number) => void;
  spacingMs: number;
  setSpacingMs: (n: number) => void;
  status: SimStatus;
  errorMsg: string | null;
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
}

const PRESETS = [
  { label: "1", value: 1 },
  { label: "10", value: 10 },
  { label: "100", value: 100 },
  { label: "1K", value: 1000 },
  { label: "10K", value: 10000 },
];

export function ControlPanel(props: ControlPanelProps) {
  const {
    count, setCount,
    registerProbability, setRegisterProbability,
    labProbability, setLabProbability,
    rxProbability, setRxProbability,
    maxConcurrency, setMaxConcurrency,
    spacingMs, setSpacingMs,
    status, errorMsg,
    onStart, onStop, onReset,
  } = props;

  const running = status === "running";

  return (
    <div className="glass rounded-2xl border border-border shadow-sm p-5 space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Run a simulation</h2>
          <p className="text-xs text-muted-foreground">
            Each journey makes 5–12 real calls across patient · appointment · lab · prescription · billing.
          </p>
        </div>
        <span
          className={cn(
            "text-xs px-2 py-1 rounded-full font-medium tabular-nums",
            status === "running" && "bg-emerald-100 text-emerald-800",
            status === "completed" && "bg-sky-100 text-sky-800",
            status === "error" && "bg-red-100 text-red-800",
            status === "idle" && "bg-gray-100 text-gray-700",
          )}
        >
          {status === "running" ? "● running"
            : status === "completed" ? "● completed"
            : status === "error" ? "● error"
            : "○ idle"}
        </span>
      </div>

      {/* Patient count: slider + numeric input + presets */}
      <div className="space-y-2">
        <div className="flex items-baseline justify-between">
          <label className="text-sm font-medium" htmlFor="count">
            Patient flows
          </label>
          <span className="text-sm tabular-nums font-semibold">
            {count.toLocaleString()}
          </span>
        </div>
        <input
          id="count"
          type="range"
          min={1}
          max={10000}
          step={1}
          value={count}
          disabled={running}
          onChange={(e) => setCount(parseInt(e.target.value, 10))}
          className="w-full accent-[var(--primary)]"
        />
        <div className="flex items-center gap-2 flex-wrap">
          {PRESETS.map((preset) => (
            <button
              key={preset.value}
              disabled={running}
              onClick={() => setCount(preset.value)}
              className={cn(
                "text-xs px-2.5 py-1 rounded-full border transition-colors",
                count === preset.value
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-white text-foreground border-border hover:bg-muted",
                running && "opacity-50 cursor-not-allowed",
              )}
            >
              {preset.label}
            </button>
          ))}
          <input
            type="number"
            min={1}
            max={10000}
            value={count}
            disabled={running}
            onChange={(e) => {
              const v = parseInt(e.target.value, 10);
              if (!Number.isNaN(v)) setCount(Math.max(1, Math.min(10000, v)));
            }}
            className="ml-auto w-24 text-right text-sm tabular-nums rounded-md border border-border bg-white px-2 py-1"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Slider
          label="New patient %"
          value={registerProbability}
          onChange={setRegisterProbability}
          disabled={running}
          help="Probability of registering a new patient (POST /patients) vs reusing an existing one."
        />
        <Slider
          label="Lab order %"
          value={labProbability}
          onChange={setLabProbability}
          disabled={running}
          help="Probability that a visit results in a lab order."
        />
        <Slider
          label="Prescription %"
          value={rxProbability}
          onChange={setRxProbability}
          disabled={running}
          help="Probability that a visit produces a new prescription."
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <div className="flex items-baseline justify-between">
            <label className="text-sm font-medium">Max concurrency</label>
            <span className="text-sm tabular-nums">{maxConcurrency}</span>
          </div>
          <input
            type="range"
            min={1}
            max={64}
            step={1}
            value={maxConcurrency}
            disabled={running}
            onChange={(e) => setMaxConcurrency(parseInt(e.target.value, 10))}
            className="w-full accent-[var(--primary)]"
          />
          <p className="text-[11px] text-muted-foreground">
            Max in-flight journeys at any moment.
          </p>
        </div>

        <div className="space-y-1.5">
          <div className="flex items-baseline justify-between">
            <label className="text-sm font-medium">Arrival spacing</label>
            <span className="text-sm tabular-nums">{spacingMs} ms</span>
          </div>
          <input
            type="range"
            min={0}
            max={1000}
            step={10}
            value={spacingMs}
            disabled={running}
            onChange={(e) => setSpacingMs(parseInt(e.target.value, 10))}
            className="w-full accent-[var(--primary)]"
          />
          <p className="text-[11px] text-muted-foreground">
            Delay between successive patient arrivals.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 pt-2">
        {!running ? (
          <button
            onClick={onStart}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
          >
            <Play size={14} /> Start simulation
          </button>
        ) : (
          <button
            onClick={onStop}
            className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
          >
            <Pause size={14} /> Stop
          </button>
        )}
        <button
          onClick={onReset}
          disabled={running}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-lg border border-border bg-white px-4 py-2 text-sm font-medium hover:bg-muted transition-colors",
            running && "opacity-50 cursor-not-allowed",
          )}
        >
          <RotateCcw size={14} /> Reset
        </button>
      </div>

      {errorMsg && (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800">
          {errorMsg}
        </div>
      )}
    </div>
  );
}

function Slider(props: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  disabled?: boolean;
  help?: string;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between">
        <label className="text-sm font-medium">{props.label}</label>
        <span className="text-sm tabular-nums">{Math.round(props.value * 100)}%</span>
      </div>
      <input
        type="range"
        min={0}
        max={100}
        step={1}
        value={Math.round(props.value * 100)}
        disabled={props.disabled}
        onChange={(e) => props.onChange(parseInt(e.target.value, 10) / 100)}
        className="w-full accent-[var(--primary)]"
      />
      {props.help && (
        <p className="text-[11px] text-muted-foreground">{props.help}</p>
      )}
    </div>
  );
}
