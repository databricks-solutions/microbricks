import { useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import { CLIENTS } from "@/lib/content";

const ALL_BFFS = [
  { name: "BFF Portal", label: "Portal composition", color: "oklch(0.7 0.18 250)" },
  { name: "BFF Mobile", label: "Mobile aggregation", color: "oklch(0.7 0.16 300)" },
  { name: "BFF Partner", label: "Partner API gateway", color: "oklch(0.7 0.14 50)" },
  { name: "BFF Analytics", label: "BI data surface", color: "oklch(0.7 0.16 200)" },
  { name: "BFF Embedded", label: "Embedded widgets", color: "oklch(0.7 0.14 330)" },
  { name: "BFF Internal", label: "Internal tooling", color: "oklch(0.7 0.16 120)" },
  { name: "BFF Webhooks", label: "Event delivery", color: "oklch(0.7 0.15 90)" },
  { name: "BFF Admin", label: "Back-office ops", color: "oklch(0.7 0.14 15)" },
  { name: "BFF Public", label: "Public read API", color: "oklch(0.7 0.16 260)" },
  { name: "BFF Realtime", label: "Streaming gateway", color: "oklch(0.7 0.15 155)" },
] as const;

const ALL_SERVICES = [
  { name: "Patients", color: "oklch(0.7 0.18 250)" },
  { name: "Scheduling", color: "oklch(0.7 0.15 175)" },
  { name: "Billing", color: "oklch(0.7 0.16 145)" },
  { name: "Clinical", color: "oklch(0.7 0.16 300)" },
  { name: "Inventory", color: "oklch(0.7 0.14 50)" },
  { name: "Messaging", color: "oklch(0.7 0.16 200)" },
] as const;

export function ServiceTopologyDiagram() {
  const [scale, setScale] = useState(3);
  const [splitServices, setSplitServices] = useState<Set<string>>(new Set());
  const [splitBffs, setSplitBffs] = useState<Set<string>>(new Set());

  const toggleService = useCallback((name: string) => {
    setSplitServices((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }, []);

  const toggleBff = useCallback((name: string) => {
    setSplitBffs((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }, []);

  const { bffs, services } = useMemo(() => {
    const svcCount = Math.min(scale, ALL_SERVICES.length);
    const bffCount = Math.min(
      scale <= ALL_SERVICES.length ? Math.min(scale, 2) : 2 + (scale - ALL_SERVICES.length),
      ALL_BFFS.length
    );
    return {
      bffs: ALL_BFFS.slice(0, bffCount),
      services: ALL_SERVICES.slice(0, svcCount),
    };
  }, [scale]);

  const hasSplits = splitServices.size > 0 || splitBffs.size > 0;

  const svcCount = services.length;
  const bffCount = bffs.length;
  const rowHeight = 72;
  const maxRows = Math.max(svcCount, bffCount);
  const contentHeight = Math.max(280, maxRows * rowHeight + 60);
  const footerPadding = hasSplits ? 76 : 50;
  const svgHeight = contentHeight + footerPadding;

  const svcSpacing = svcCount > 1 ? Math.min(rowHeight, (contentHeight - 80) / (svcCount - 1)) : 0;
  const bffSpacing = bffCount > 1 ? Math.min(90, (contentHeight - 80) / (bffCount - 1)) : 0;

  const svcStartY = 40 + (contentHeight - 80 - (svcCount - 1) * svcSpacing) / 2;
  const bffStartY = 40 + (contentHeight - 80 - (bffCount - 1) * bffSpacing) / 2;
  const clientStartY = 40 + (contentHeight - 80 - (CLIENTS.length - 1) * 60) / 2;

  const servicesLocked = scale > ALL_SERVICES.length;

  return (
    <div className="relative w-full max-w-5xl mx-auto py-6">
      {/* ─── Control Bar ─── */}
      <div className="mb-6 px-4">
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted-foreground uppercase tracking-wider shrink-0">Scale</span>
          <div className="relative flex-1">
            <input
              type="range"
              min={2}
              max={ALL_SERVICES.length + ALL_BFFS.length - 2}
              value={scale}
              onChange={(e) => setScale(Number(e.target.value))}
              className="w-full h-1.5 rounded-full appearance-none cursor-pointer bg-border [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary [&::-webkit-slider-thumb]:shadow-md [&::-webkit-slider-thumb]:cursor-grab [&::-webkit-slider-thumb]:active:cursor-grabbing"
            />
            {servicesLocked && (
              <div
                className="absolute top-0 h-1.5 rounded-l-full bg-muted-foreground/20 pointer-events-none"
                style={{
                  left: 0,
                  width: `${((ALL_SERVICES.length - 2) / (ALL_SERVICES.length + ALL_BFFS.length - 4)) * 100}%`,
                }}
              />
            )}
          </div>
        </div>
        <div className="flex justify-between mt-2 text-sm text-muted-foreground">
          <div className="flex gap-4">
            <span>
              <span className="font-medium text-foreground">{bffCount}</span> BFF{bffCount > 1 ? "s" : ""}
            </span>
            <span>
              <span className="font-medium text-foreground">{svcCount}</span> Service{svcCount > 1 ? "s" : ""}
              {servicesLocked && <span className="ml-1 text-muted-foreground/60">(domain-bounded)</span>}
            </span>
            <span>
              <span className="font-medium text-foreground">{svcCount}</span> DB{svcCount > 1 ? "s" : ""}
            </span>
          </div>
          {servicesLocked && (
            <span className="text-primary/80 italic">+ BFFs scale independently</span>
          )}
        </div>
      </div>

      {/* ─── SVG Diagram ─── */}
      <svg viewBox={`0 0 960 ${svgHeight}`} className="w-full h-auto transition-all duration-300" fill="none">
        {/* ─── Column Labels ─── */}
        <text x="80" y="18" textAnchor="middle" className="text-[12px] fill-muted-foreground/60 uppercase tracking-wider">Clients</text>
        <text x="275" y="18" textAnchor="middle" className="text-[12px] fill-muted-foreground/60 uppercase tracking-wider">BFF Layer</text>
        <text x="560" y="18" textAnchor="middle" className="text-[12px] fill-muted-foreground/60 uppercase tracking-wider">Domain Services</text>
        <text x="790" y="18" textAnchor="middle" className="text-[12px] fill-muted-foreground/60 uppercase tracking-wider">Data</text>

        {/* ─── CLIENTS (left) ─── */}
        {CLIENTS.map((client, i) => {
          const y = clientStartY + i * 60;
          return (
            <g key={client.name}>
              <rect x="30" y={y} width="100" height="40" rx="10" className="fill-card stroke-border" strokeWidth="1.5" />
              <text x="80" y={y + 24} textAnchor="middle" className="fill-foreground text-sm font-medium">{client.name}</text>
            </g>
          );
        })}

        {/* ─── BFF LAYER ─── */}
        <AnimatePresence>
          {bffs.map((bff, i) => {
            const y = bffStartY + i * bffSpacing;
            const isSplit = splitBffs.has(bff.name);
            return (
              <motion.g
                key={bff.name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
                style={{ cursor: "pointer" }}
                onClick={() => toggleBff(bff.name)}
              >
                {!isSplit ? (
                  <>
                    <rect x="210" y={y} width="130" height="64" rx="12" stroke={bff.color} strokeWidth="2" fill={`${bff.color} / 0.06`} />
                    <text x="275" y={y + 26} textAnchor="middle" className="text-sm font-bold" fill={bff.color}>{bff.name}</text>
                    <text x="275" y={y + 42} textAnchor="middle" className="text-[10px] fill-muted-foreground">{bff.label}</text>
                    <text x="275" y={y + 56} textAnchor="middle" className="text-[9px] fill-muted-foreground/50">click to split</text>
                  </>
                ) : (
                  <>
                    {/* v1 — top half, dimmed */}
                    <rect x="210" y={y} width="130" height="29" rx="8" stroke={bff.color} strokeWidth="1.5" fill={`${bff.color} / 0.04`} opacity="0.6" />
                    <text x="275" y={y + 13} textAnchor="middle" className="text-[10px] font-semibold" fill={bff.color} opacity="0.6">{bff.name}</text>
                    <text x="275" y={y + 24} textAnchor="middle" className="text-[9px] fill-muted-foreground" opacity="0.6">v1 · production</text>

                    {/* v2 — bottom half, highlighted */}
                    <motion.rect
                      x="210" y={y + 33} width="130" height="29" rx="8"
                      stroke={bff.color} strokeWidth="2.5"
                      fill={`${bff.color} / 0.12`}
                      animate={{ strokeOpacity: [1, 0.5, 1] }}
                      transition={{ duration: 2, repeat: Infinity }}
                    />
                    <text x="275" y={y + 46} textAnchor="middle" className="text-[10px] font-bold" fill={bff.color}>{bff.name}</text>
                    <text x="275" y={y + 57} textAnchor="middle" className="text-[9px]" fill={bff.color}>v2 · new branch</text>
                  </>
                )}
              </motion.g>
            );
          })}
        </AnimatePresence>

        {/* Connections: Clients → BFFs */}
        {CLIENTS.map((_, ci) => {
          const cy = clientStartY + ci * 60 + 20;
          return bffs.map((_, bi) => {
            const by = bffStartY + bi * bffSpacing + 32;
            return (
              <line
                key={`c${ci}-b${bi}`}
                x1="130" y1={cy} x2="210" y2={by}
                className="stroke-border"
                strokeWidth="1"
                strokeDasharray="4 3"
              />
            );
          });
        })}

        {/* ─── DOMAIN SERVICES + DATABASES (right) ─── */}
        <AnimatePresence>
          {services.map((svc, i) => {
            const y = svcStartY + i * svcSpacing;
            const svcX = 490;
            const dbX = 790;
            const isSplit = splitServices.has(svc.name);

            return (
              <motion.g
                key={svc.name}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.3 }}
              >
                {!isSplit ? (
                  <>
                    {/* Service box (clickable) */}
                    <g style={{ cursor: "pointer" }} onClick={() => toggleService(svc.name)}>
                      <rect x={svcX} y={y} width="140" height="48" rx="10" fill={`${svc.color} / 0.06`} stroke={svc.color} strokeWidth="1.5" />
                      <text x={svcX + 70} y={y + 22} textAnchor="middle" className="text-sm font-semibold" fill={svc.color}>{svc.name}</text>
                      <text x={svcX + 70} y={y + 36} textAnchor="middle" className="text-[9px] fill-muted-foreground">click to split</text>
                    </g>

                    {/* Connection: Service → DB */}
                    <line
                      x1={svcX + 140} y1={y + 24} x2={dbX - 34} y2={y + 24}
                      stroke={svc.color}
                      strokeWidth="1"
                      strokeDasharray="4 3"
                      opacity="0.4"
                    />

                    {/* Database cylinder */}
                    <ellipse cx={dbX} cy={y + 12} rx="30" ry="7" fill={`${svc.color} / 0.08`} stroke={svc.color} strokeWidth="1" />
                    <rect x={dbX - 30} y={y + 12} width="60" height="22" fill={`${svc.color} / 0.08`} stroke="none" />
                    <line x1={dbX - 30} y1={y + 12} x2={dbX - 30} y2={y + 34} stroke={svc.color} strokeWidth="1" />
                    <line x1={dbX + 30} y1={y + 12} x2={dbX + 30} y2={y + 34} stroke={svc.color} strokeWidth="1" />
                    <ellipse cx={dbX} cy={y + 34} rx="30" ry="7" fill={`${svc.color} / 0.08`} stroke={svc.color} strokeWidth="1" />
                    <text x={dbX} y={y + 27} textAnchor="middle" className="text-[9px] fill-muted-foreground">Lakebase</text>
                  </>
                ) : (
                  <>
                    {/* Split service: v1 top (dimmed) */}
                    <g style={{ cursor: "pointer" }} onClick={() => toggleService(svc.name)}>
                      <rect x={svcX} y={y} width="140" height="22" rx="6" fill={`${svc.color} / 0.04`} stroke={svc.color} strokeWidth="1" opacity="0.6" />
                      <text x={svcX + 70} y={y + 14} textAnchor="middle" className="text-[11px] font-semibold" fill={svc.color} opacity="0.6">{svc.name} v1</text>

                      {/* Split service: v2 bottom (highlighted) */}
                      <motion.rect
                        x={svcX} y={y + 26} width="140" height="22" rx="6"
                        fill={`${svc.color} / 0.12`} stroke={svc.color} strokeWidth="2"
                        animate={{ strokeOpacity: [1, 0.4, 1] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      />
                      <text x={svcX + 70} y={y + 40} textAnchor="middle" className="text-[11px] font-bold" fill={svc.color}>{svc.name} v2</text>
                    </g>

                    {/* Connection: v1 → prod DB */}
                    <line
                      x1={svcX + 140} y1={y + 11} x2={dbX - 50} y2={y + 11}
                      stroke={svc.color}
                      strokeWidth="1"
                      strokeDasharray="4 3"
                      opacity="0.3"
                    />
                    {/* Connection: v2 → branch DB */}
                    <line
                      x1={svcX + 140} y1={y + 37} x2={dbX - 50} y2={y + 37}
                      stroke={svc.color}
                      strokeWidth="1.5"
                      strokeDasharray="4 3"
                      opacity="0.8"
                    />

                    {/* Prod DB cylinder (left, smaller, dimmed) */}
                    <g opacity="0.5">
                      <ellipse cx={dbX - 20} cy={y + 6} rx="20" ry="5" fill={`${svc.color} / 0.06`} stroke={svc.color} strokeWidth="0.8" />
                      <rect x={dbX - 40} y={y + 6} width="40" height="14" fill={`${svc.color} / 0.06`} stroke="none" />
                      <line x1={dbX - 40} y1={y + 6} x2={dbX - 40} y2={y + 20} stroke={svc.color} strokeWidth="0.8" />
                      <line x1={dbX} y1={y + 6} x2={dbX} y2={y + 20} stroke={svc.color} strokeWidth="0.8" />
                      <ellipse cx={dbX - 20} cy={y + 20} rx="20" ry="5" fill={`${svc.color} / 0.06`} stroke={svc.color} strokeWidth="0.8" />
                      <text x={dbX - 20} y={y + 15} textAnchor="middle" className="text-[8px] fill-muted-foreground">prod</text>
                    </g>

                    {/* Branch DB cylinder (right, highlighted) */}
                    <g>
                      <motion.ellipse
                        cx={dbX + 22} cy={y + 28} rx="20" ry="5"
                        fill={`${svc.color} / 0.12`} stroke={svc.color} strokeWidth="1.2"
                        animate={{ strokeOpacity: [1, 0.5, 1] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      />
                      <rect x={dbX + 2} y={y + 28} width="40" height="14" fill={`${svc.color} / 0.12`} stroke="none" />
                      <line x1={dbX + 2} y1={y + 28} x2={dbX + 2} y2={y + 42} stroke={svc.color} strokeWidth="1.2" />
                      <line x1={dbX + 42} y1={y + 28} x2={dbX + 42} y2={y + 42} stroke={svc.color} strokeWidth="1.2" />
                      <motion.ellipse
                        cx={dbX + 22} cy={y + 42} rx="20" ry="5"
                        fill={`${svc.color} / 0.12`} stroke={svc.color} strokeWidth="1.2"
                        animate={{ strokeOpacity: [1, 0.5, 1] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      />
                      <text x={dbX + 22} y={y + 38} textAnchor="middle" className="text-[9px] font-semibold" fill={svc.color}>v2-branch</text>
                    </g>

                    {/* Fork line connecting the two DBs */}
                    <line x1={dbX - 20} y1={y + 6} x2={dbX + 22} y2={y + 28} stroke={svc.color} strokeWidth="0.8" strokeDasharray="2 2" opacity="0.4" />
                  </>
                )}
              </motion.g>
            );
          })}
        </AnimatePresence>

        {/* Connections: BFFs → Services */}
        {bffs.map((bff, bi) => {
          const bffIsSplit = splitBffs.has(bff.name);
          const bffY = bffStartY + bi * bffSpacing;
          return services.map((svc, si) => {
            const svcIsSplit = splitServices.has(svc.name);
            const svcY = svcStartY + si * svcSpacing;

            if (!bffIsSplit && !svcIsSplit) {
              return (
                <line
                  key={`b${bi}-s${si}`}
                  x1="340" y1={bffY + 32} x2="490" y2={svcY + 24}
                  className="stroke-border"
                  strokeWidth="0.8"
                  strokeDasharray="4 3"
                />
              );
            }

            const lines = [];
            // v1 BFF → v1 service
            lines.push(
              <line
                key={`b${bi}-s${si}-v1`}
                x1="340" y1={bffIsSplit ? bffY + 14 : bffY + 32}
                x2="490" y2={svcIsSplit ? svcY + 11 : svcY + 24}
                className="stroke-border"
                strokeWidth="0.6"
                strokeDasharray="4 3"
                opacity="0.4"
              />
            );
            // v2 BFF → v2 service (only if BFF is split)
            if (bffIsSplit) {
              lines.push(
                <line
                  key={`b${bi}-s${si}-v2`}
                  x1="340" y1={bffY + 47}
                  x2="490" y2={svcIsSplit ? svcY + 37 : svcY + 24}
                  stroke={bff.color}
                  strokeWidth="1.2"
                  strokeDasharray="4 3"
                  opacity="0.7"
                />
              );
            }
            return lines;
          });
        })}

        {/* ─── KEY RULE / INFO BANNER ─── */}
        {!hasSplits ? (
          <g>
            <rect x="160" y={contentHeight + 30} width="640" height="24" rx="6" fill="oklch(0.78 0.16 75 / 0.06)" stroke="oklch(0.78 0.16 75 / 0.2)" strokeWidth="1" />
            <text x="480" y={contentHeight + 45} textAnchor="middle" className="text-[10px]" fill="oklch(0.78 0.16 75)">
              No cross-database joins · No backend-to-backend calls · BFFs fan out, compose in memory
            </text>
          </g>
        ) : (
          <g>
            <rect x="100" y={contentHeight + 31} width="760" height="44" rx="8" fill="oklch(0.7 0.18 250 / 0.06)" stroke="oklch(0.7 0.18 250 / 0.3)" strokeWidth="1.5" />
            <text x="480" y={contentHeight + 49} textAnchor="middle" className="text-[12px] font-semibold" fill="oklch(0.7 0.18 250)">
              Breaking change: v2 deploys with a new Lakebase branch
            </text>
            <text x="480" y={contentHeight + 65} textAnchor="middle" className="text-[10px]" fill="oklch(0.7 0.14 250)">
              v1 continues serving production traffic on the original branch until new v* tag released. Click again to revert
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}
