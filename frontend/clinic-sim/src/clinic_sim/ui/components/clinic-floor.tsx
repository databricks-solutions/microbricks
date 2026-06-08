/**
 * Clinic floor: the visible room grid + per-room avatars.
 *
 * Architecture: the rooms are static boxes laid out in a CSS grid. Avatars
 * live on a single absolutely-positioned overlay layer above them — one
 * `motion.div` per patient, with `x/y` driven by the measured rect of
 * whatever room the patient is currently in. Stage changes therefore
 * animate the *same* DOM node from one room to the next; we never
 * unmount/remount an avatar, so there is no fade-out/fade-in flicker as
 * patients move between rooms.
 *
 * Room positions are measured with ResizeObserver on the container so the
 * layer follows the responsive grid (1/3/6 cols) on resize.
 */
import { AnimatePresence, motion } from "motion/react";
import { useLayoutEffect, useMemo, useRef, useState } from "react";

import { PersonAvatar } from "./person-avatar";
import type { Stage } from "@/lib/stream";

export interface RoomDef {
  key: Stage;
  label: string;
  emoji: string;
  /** Tailwind background classes for the room interior. */
  bg: string;
  /** Tailwind ring/border color. */
  ring: string;
  /** Order index for the floor layout. */
  order: number;
}

export const ROOMS: RoomDef[] = [
  { key: "reception", label: "Reception",    emoji: "🪪", bg: "bg-sky-100",     ring: "ring-sky-300",     order: 0 },
  { key: "waiting",   label: "Waiting Room", emoji: "🪑", bg: "bg-amber-100",   ring: "ring-amber-300",   order: 1 },
  { key: "exam",      label: "Exam Room",    emoji: "🩺", bg: "bg-emerald-100", ring: "ring-emerald-300", order: 2 },
  { key: "lab",       label: "Lab",          emoji: "🧪", bg: "bg-violet-100",  ring: "ring-violet-300",  order: 3 },
  { key: "pharmacy",  label: "Pharmacy",     emoji: "💊", bg: "bg-rose-100",    ring: "ring-rose-300",    order: 4 },
  { key: "checkout",  label: "Checkout",     emoji: "🧾", bg: "bg-teal-100",    ring: "ring-teal-300",    order: 5 },
];

export interface ActivePatient {
  journey_id: number;
  patient_name: string;
  stage: Stage;
  patient_id?: string | null;
}

interface FloorProps {
  patients: ActivePatient[];
  /** Optional cap on how many avatars to render per room. */
  perRoomMax?: number;
}

interface RoomRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

const AVATAR_W = 24;
const AVATAR_H = AVATAR_W * 1.5;
const ROOM_PAD_X = 10;
const ROOM_PAD_TOP = 30; // leave room for the room title
const ROOM_PAD_BOTTOM = 8;

/**
 * Group patients by stage. Patients in non-room stages (`entering`,
 * `leaving`, `done`, `failed`) are routed to a virtual room so the UI can
 * still display the count without rendering them on the main floor.
 */
function groupByStage(patients: ActivePatient[]): Map<Stage, ActivePatient[]> {
  const map = new Map<Stage, ActivePatient[]>();
  for (const p of patients) {
    const list = map.get(p.stage) ?? [];
    list.push(p);
    map.set(p.stage, list);
  }
  return map;
}

/**
 * Deterministic but jittered position inside a measured room rect.
 * Same `seed` always lands on the same spot for the same room so a patient
 * doesn't appear to teleport around within a room between renders.
 */
function jitterPos(seed: number, rect: RoomRect) {
  const rx = ((seed * 9301 + 49297) % 233280) / 233280;
  const ry = ((seed * 7457 + 12345) % 233280) / 233280;
  const innerW = Math.max(0, rect.width - ROOM_PAD_X * 2 - AVATAR_W);
  const innerH = Math.max(0, rect.height - ROOM_PAD_TOP - ROOM_PAD_BOTTOM - AVATAR_H);
  return {
    x: rect.x + ROOM_PAD_X + Math.round(rx * innerW),
    y: rect.y + ROOM_PAD_TOP + Math.round(ry * innerH),
  };
}

export function ClinicFloor({ patients, perRoomMax = 18 }: FloorProps) {
  const byStage = useMemo(() => groupByStage(patients), [patients]);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const roomRefs = useRef<Partial<Record<Stage, HTMLDivElement | null>>>({});
  const [roomRects, setRoomRects] = useState<Partial<Record<Stage, RoomRect>>>({});

  // Measure each room rect relative to the container. Re-measure on resize.
  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const measure = () => {
      const cRect = container.getBoundingClientRect();
      const next: Partial<Record<Stage, RoomRect>> = {};
      let changed = false;
      for (const room of ROOMS) {
        const el = roomRefs.current[room.key];
        if (!el) continue;
        const r = el.getBoundingClientRect();
        const rect: RoomRect = {
          x: r.x - cRect.x,
          y: r.y - cRect.y,
          width: r.width,
          height: r.height,
        };
        next[room.key] = rect;
        const prev = roomRects[room.key];
        if (
          !prev ||
          prev.x !== rect.x ||
          prev.y !== rect.y ||
          prev.width !== rect.width ||
          prev.height !== rect.height
        ) {
          changed = true;
        }
      }
      if (changed) setRoomRects(next);
    };

    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(container);
    window.addEventListener("resize", measure);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measure);
    };
    // We intentionally only run this once on mount and rely on
    // ResizeObserver from there. Re-running on every roomRects change
    // would create an observer-update loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Per-stage occupant cap: we render at most `perRoomMax` avatars in any
  // single room, but the parent has already capped the total list size.
  // We rank by journey_id within a room so the "kept" avatars are stable
  // — a patient that was visible in a room will keep their slot.
  const visiblePatients = useMemo(() => {
    const out: ActivePatient[] = [];
    for (const room of ROOMS) {
      const list = byStage.get(room.key) ?? [];
      // Ascending journey_id: older patients stay rendered, newer ones
      // overflow once a room is full. Keeps the visible set stable.
      const ranked = [...list].sort((a, b) => a.journey_id - b.journey_id);
      for (const p of ranked.slice(0, perRoomMax)) out.push(p);
    }
    return out;
  }, [byStage, perRoomMax]);

  return (
    <div
      ref={containerRef}
      className="relative w-full rounded-2xl border border-border bg-white shadow-sm overflow-hidden"
    >
      <div className="floor-tile absolute inset-0 opacity-30 pointer-events-none" />

      {/* Static room grid — no avatars live inside the rooms, just headers
          and the overflow badge. Avatars sit on an overlay layer below. */}
      <div className="relative grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3 p-4">
        {ROOMS.map((room) => {
          const total = byStage.get(room.key)?.length ?? 0;
          const overflow = Math.max(0, total - perRoomMax);
          return (
            <div
              key={room.key}
              ref={(el) => {
                roomRefs.current[room.key] = el;
              }}
              className={`relative h-56 rounded-xl ring-1 ${room.ring} ${room.bg} p-2 flex flex-col`}
            >
              <div className="flex items-center justify-between text-xs font-medium text-gray-800">
                <span className="flex items-center gap-1.5">
                  <span aria-hidden>{room.emoji}</span>
                  <span>{room.label}</span>
                </span>
                <span className="rounded-full bg-white/70 px-2 py-0.5 text-[10px] tabular-nums font-semibold text-gray-900">
                  {total}
                </span>
              </div>

              {overflow > 0 && (
                <div className="absolute bottom-2 right-2 text-[10px] font-semibold rounded-full bg-black/70 text-white px-1.5 py-0.5">
                  +{overflow}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Avatars overlay: ONE motion.div per patient. The `key` is just the
          journey_id (no room name) so a patient is the same DOM node from
          reception → checkout, and only their x/y animate when they move. */}
      <div className="absolute inset-0 pointer-events-none">
        <AnimatePresence>
          {visiblePatients.map((p) => {
            const rect = roomRects[p.stage];
            if (!rect) return null;
            const room = ROOMS.find((r) => r.key === p.stage);
            const pos = jitterPos(p.journey_id + (room?.order ?? 0) * 17, rect);
            return (
              <motion.div
                key={`p-${p.journey_id}`}
                initial={{ opacity: 0, scale: 0.6, x: pos.x, y: pos.y }}
                animate={{
                  opacity: 1,
                  scale: 1,
                  x: pos.x,
                  y: pos.y,
                }}
                exit={{ opacity: 0, scale: 0.6, transition: { duration: 0.25 } }}
                transition={{
                  // Slow, walking-pace movement so the eye can follow a
                  // single patient as they cross between rooms.
                  x: { duration: 1.4, ease: [0.4, 0, 0.2, 1] },
                  y: { duration: 1.4, ease: [0.4, 0, 0.2, 1] },
                  opacity: { duration: 0.35 },
                  scale: { duration: 0.35 },
                }}
                className="absolute left-0 top-0"
                title={`${p.patient_name} (#${p.journey_id})`}
              >
                <PersonAvatar size={AVATAR_W} seed={p.journey_id} walking={false} />
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* Bottom legend: entering / leaving / failed counts */}
      <div className="relative border-t border-border bg-muted/50 px-4 py-2 text-[11px] text-muted-foreground flex flex-wrap items-center gap-4">
        <span>
          ↳ Entering:{" "}
          <span className="font-semibold text-foreground tabular-nums">
            {byStage.get("entering")?.length ?? 0}
          </span>
        </span>
        <span>
          ↲ Leaving:{" "}
          <span className="font-semibold text-foreground tabular-nums">
            {byStage.get("leaving")?.length ?? 0}
          </span>
        </span>
        <span>
          ✓ Done:{" "}
          <span className="font-semibold text-emerald-700 tabular-nums">
            {byStage.get("done")?.length ?? 0}
          </span>
        </span>
        <span>
          ✗ Failed:{" "}
          <span className="font-semibold text-red-700 tabular-nums">
            {byStage.get("failed")?.length ?? 0}
          </span>
        </span>
      </div>
    </div>
  );
}
