import { motion } from "motion/react";
import { SERVICES, CLIENTS } from "@/lib/content";

const BFFS = [
  { name: "BFF Portal", label: "Portal composition", color: "oklch(0.7 0.18 250)" },
  { name: "BFF Mobile", label: "Mobile aggregation", color: "oklch(0.7 0.16 300)" },
] as const;

export function ServiceTopologyDiagram() {
  return (
    <div className="relative w-full max-w-5xl mx-auto py-8">
      <svg viewBox="0 0 960 420" className="w-full h-auto" fill="none">
        {/* ─── CLIENTS (left) ─── */}
        {CLIENTS.map((client, i) => {
          const y = 80 + i * 70;
          return (
            <motion.g
              key={client.name}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.4 }}
            >
              <rect x="30" y={y} width="100" height="44" rx="10" className="fill-card stroke-border" strokeWidth="1.5" />
              <text x="80" y={y + 26} textAnchor="middle" className="fill-foreground text-[11px] font-medium">{client.name}</text>
            </motion.g>
          );
        })}

        {/* ─── BFF LAYER (center-left) ─── */}
        {BFFS.map((bff, i) => {
          const y = 95 + i * 120;
          return (
            <motion.g
              key={bff.name}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.3 + i * 0.15, duration: 0.5 }}
            >
              <rect x="210" y={y} width="130" height="80" rx="12" stroke={bff.color} strokeWidth="2" fill={`${bff.color} / 0.06`} />
              <text x="275" y={y + 32} textAnchor="middle" className="text-[12px] font-bold" fill={bff.color}>{bff.name}</text>
              <text x="275" y={y + 50} textAnchor="middle" className="text-[9px] fill-muted-foreground">{bff.label}</text>
              <text x="275" y={y + 66} textAnchor="middle" className="text-[8px] fill-muted-foreground/60">fan-out + compose</text>
            </motion.g>
          );
        })}

        {/* Connections: Clients → BFFs */}
        {CLIENTS.map((_, ci) => {
          const cy = 102 + ci * 70;
          return BFFS.map((_, bi) => {
            const by = 135 + bi * 120;
            return (
              <motion.line
                key={`c${ci}-b${bi}`}
                x1="130" y1={cy} x2="210" y2={by}
                className="stroke-border"
                strokeWidth="1"
                strokeDasharray="4 3"
                initial={{ pathLength: 0 }}
                whileInView={{ pathLength: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.2 + ci * 0.05 + bi * 0.05, duration: 0.3 }}
              />
            );
          });
        })}

        {/* ─── DOMAIN SERVICES + DATABASES (right) ─── */}
        {SERVICES.map((svc, i) => {
          const y = 50 + i * 90;
          const svcX = 480;
          const dbX = 760;

          return (
            <motion.g
              key={svc.name}
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.5 + i * 0.1, duration: 0.4 }}
            >
              {/* Service rounded box */}
              <rect x={svcX} y={y} width="140" height="58" rx="10" fill={`${svc.color} / 0.06`} stroke={svc.color} strokeWidth="1.5" />
              <text x={svcX + 70} y={y + 25} textAnchor="middle" className="text-[11px] font-semibold" fill={svc.color}>{svc.name}</text>
              <text x={svcX + 70} y={y + 42} textAnchor="middle" className="text-[8px] fill-muted-foreground">Databricks App</text>

              {/* Connection: Service → DB */}
              <motion.line
                x1={svcX + 140} y1={y + 29} x2={dbX - 40} y2={y + 29}
                stroke={svc.color}
                strokeWidth="1"
                strokeDasharray="4 3"
                opacity="0.5"
                initial={{ pathLength: 0 }}
                whileInView={{ pathLength: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.8 + i * 0.08, duration: 0.3 }}
              />

              {/* Database cylinder */}
              <ellipse cx={dbX} cy={y + 16} rx="34" ry="8" fill={`${svc.color} / 0.08`} stroke={svc.color} strokeWidth="1" />
              <rect x={dbX - 34} y={y + 16} width="68" height="26" fill={`${svc.color} / 0.08`} stroke="none" />
              <line x1={dbX - 34} y1={y + 16} x2={dbX - 34} y2={y + 42} stroke={svc.color} strokeWidth="1" />
              <line x1={dbX + 34} y1={y + 16} x2={dbX + 34} y2={y + 42} stroke={svc.color} strokeWidth="1" />
              <ellipse cx={dbX} cy={y + 42} rx="34" ry="8" fill={`${svc.color} / 0.08`} stroke={svc.color} strokeWidth="1" />
              <text x={dbX} y={y + 33} textAnchor="middle" className="text-[8px] fill-muted-foreground">Lakebase</text>
            </motion.g>
          );
        })}

        {/* Connections: BFFs → Services */}
        {BFFS.map((_, bi) => {
          const bffY = 135 + bi * 120;
          return SERVICES.map((_, si) => {
            const svcY = 79 + si * 90;
            return (
              <motion.line
                key={`b${bi}-s${si}`}
                x1="340" y1={bffY} x2="480" y2={svcY}
                className="stroke-border"
                strokeWidth="1"
                strokeDasharray="4 3"
                initial={{ pathLength: 0 }}
                whileInView={{ pathLength: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.5 + bi * 0.08 + si * 0.05, duration: 0.3 }}
              />
            );
          });
        })}

        {/* ─── Column Labels ─── */}
        <motion.g
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 1.0 }}
        >
          <text x="80" y="32" textAnchor="middle" className="text-[9px] fill-muted-foreground/60 uppercase tracking-wider">Clients</text>
          <text x="275" y="32" textAnchor="middle" className="text-[9px] fill-muted-foreground/60 uppercase tracking-wider">BFF Layer</text>
          <text x="550" y="32" textAnchor="middle" className="text-[9px] fill-muted-foreground/60 uppercase tracking-wider">Domain Services</text>
          <text x="760" y="32" textAnchor="middle" className="text-[9px] fill-muted-foreground/60 uppercase tracking-wider">Data</text>
        </motion.g>

        {/* ─── KEY RULE ─── */}
        <motion.g
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 1.2 }}
        >
          <rect x="160" y="390" width="640" height="26" rx="6" fill="oklch(0.78 0.16 75 / 0.06)" stroke="oklch(0.78 0.16 75 / 0.2)" strokeWidth="1" />
          <text x="480" y="407" textAnchor="middle" className="text-[9px]" fill="oklch(0.78 0.16 75)">
            No cross-database joins · No backend-to-backend calls · BFFs fan out, compose in memory
          </text>
        </motion.g>
      </svg>
    </div>
  );
}
