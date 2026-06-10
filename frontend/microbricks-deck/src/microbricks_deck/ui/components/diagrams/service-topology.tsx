import { useState, useMemo } from "react";
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

  const svcCount = services.length;
  const bffCount = bffs.length;
  const rowHeight = 72;
  const maxRows = Math.max(svcCount, bffCount);
  const contentHeight = Math.max(280, maxRows * rowHeight + 60);
  const footerPadding = 50;
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
        <text x="80" y="18" textAnchor="middle" className="text-[9px] fill-muted-foreground/60 uppercase tracking-wider">Clients</text>
        <text x="275" y="18" textAnchor="middle" className="text-[9px] fill-muted-foreground/60 uppercase tracking-wider">BFF Layer</text>
        <text x="560" y="18" textAnchor="middle" className="text-[9px] fill-muted-foreground/60 uppercase tracking-wider">Domain Services</text>
        <text x="790" y="18" textAnchor="middle" className="text-[9px] fill-muted-foreground/60 uppercase tracking-wider">Data</text>

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
            return (
              <motion.g
                key={bff.name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
              >
                <rect x="210" y={y} width="130" height="64" rx="12" stroke={bff.color} strokeWidth="2" fill={`${bff.color} / 0.06`} />
                <text x="275" y={y + 26} textAnchor="middle" className="text-sm font-bold" fill={bff.color}>{bff.name}</text>
                <text x="275" y={y + 42} textAnchor="middle" className="text-[8px] fill-muted-foreground">{bff.label}</text>
                <text x="275" y={y + 56} textAnchor="middle" className="text-[7px] fill-muted-foreground/50">fan-out + compose</text>
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

            return (
              <motion.g
                key={svc.name}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.3 }}
              >
                {/* Service box */}
                <rect x={svcX} y={y} width="140" height="48" rx="10" fill={`${svc.color} / 0.06`} stroke={svc.color} strokeWidth="1.5" />
                <text x={svcX + 70} y={y + 22} textAnchor="middle" className="text-sm font-semibold" fill={svc.color}>{svc.name}</text>
                <text x={svcX + 70} y={y + 36} textAnchor="middle" className="text-[7px] fill-muted-foreground">Databricks App</text>

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
                <text x={dbX} y={y + 27} textAnchor="middle" className="text-[7px] fill-muted-foreground">Lakebase</text>
              </motion.g>
            );
          })}
        </AnimatePresence>

        {/* Connections: BFFs → Services */}
        {bffs.map((_, bi) => {
          const bffY = bffStartY + bi * bffSpacing + 32;
          return services.map((_, si) => {
            const svcY = svcStartY + si * svcSpacing + 24;
            return (
              <line
                key={`b${bi}-s${si}`}
                x1="340" y1={bffY} x2="490" y2={svcY}
                className="stroke-border"
                strokeWidth="0.8"
                strokeDasharray="4 3"
              />
            );
          });
        })}

        {/* ─── KEY RULE ─── */}
        <g>
          <rect x="160" y={contentHeight + 10} width="640" height="24" rx="6" fill="oklch(0.78 0.16 75 / 0.06)" stroke="oklch(0.78 0.16 75 / 0.2)" strokeWidth="1" />
          <text x="480" y={contentHeight + 25} textAnchor="middle" className="text-[9px]" fill="oklch(0.78 0.16 75)">
            No cross-database joins · No backend-to-backend calls · BFFs fan out, compose in memory
          </text>
        </g>
      </svg>
    </div>
  );
}
