"use client";
import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import AuthGuard from "@/components/layout/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import Link from "next/link";
import api from "@/lib/api";
import type { GraphData, KGEntity, KGEdge } from "@/types";

const DOMAIN_COLORS: Record<string, string> = {
  mathematics: "#6366f1",
  physics: "#f59e0b",
  biology: "#10b981",
  chemistry: "#ef4444",
  computer_science: "#3b82f6",
  ai_ml: "#8b5cf6",
  general: "#6b7280",
};

function domainColor(domain: string) {
  return DOMAIN_COLORS[domain] ?? "#6b7280";
}

interface NodePos {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  entity: KGEntity;
}

function useForceLayout(nodes: KGEntity[], edges: KGEdge[], width: number, height: number) {
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});

  useEffect(() => {
    if (!nodes.length) return;

    const pos: Record<string, NodePos> = {};
    nodes.forEach((n, i) => {
      const angle = (2 * Math.PI * i) / nodes.length;
      pos[n.id] = {
        id: n.id,
        x: width / 2 + (width / 3) * Math.cos(angle),
        y: height / 2 + (height / 3) * Math.sin(angle),
        vx: 0,
        vy: 0,
        entity: n,
      };
    });

    const REPEL = 4000;
    const ATTRACT = 0.05;
    const CENTER = 0.01;
    const DAMPING = 0.8;
    const ITERS = 120;

    for (let iter = 0; iter < ITERS; iter++) {
      // Repulsion
      const ids = Object.keys(pos);
      for (let i = 0; i < ids.length; i++) {
        for (let j = i + 1; j < ids.length; j++) {
          const a = pos[ids[i]];
          const b = pos[ids[j]];
          const dx = b.x - a.x || 0.01;
          const dy = b.y - a.y || 0.01;
          const dist2 = dx * dx + dy * dy;
          const f = REPEL / dist2;
          a.vx -= f * dx;
          a.vy -= f * dy;
          b.vx += f * dx;
          b.vy += f * dy;
        }
      }
      // Attraction along edges
      edges.forEach((e) => {
        const s = pos[e.source];
        const t = pos[e.target];
        if (!s || !t) return;
        const dx = t.x - s.x;
        const dy = t.y - s.y;
        s.vx += ATTRACT * dx;
        s.vy += ATTRACT * dy;
        t.vx -= ATTRACT * dx;
        t.vy -= ATTRACT * dy;
      });
      // Center pull
      ids.forEach((id) => {
        pos[id].vx += CENTER * (width / 2 - pos[id].x);
        pos[id].vy += CENTER * (height / 2 - pos[id].y);
      });
      // Integrate
      ids.forEach((id) => {
        pos[id].vx *= DAMPING;
        pos[id].vy *= DAMPING;
        pos[id].x += pos[id].vx;
        pos[id].y += pos[id].vy;
        pos[id].x = Math.max(40, Math.min(width - 40, pos[id].x));
        pos[id].y = Math.max(40, Math.min(height - 40, pos[id].y));
      });
    }

    const out: Record<string, { x: number; y: number }> = {};
    Object.keys(pos).forEach((id) => { out[id] = { x: pos[id].x, y: pos[id].y }; });
    setPositions(out);
  }, [nodes, edges, width, height]);

  return positions;
}

export default function GraphPage() {
  const { id } = useParams<{ id: string }>();
  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });
  const [selected, setSelected] = useState<KGEntity | null>(null);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 800, h: 560 });

  useEffect(() => {
    if (!id) return;
    api.get(`/projects/${id}/knowledge-graph/graph`)
      .then((r) => setGraph(r.data))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      setDims({ w: el.clientWidth, h: el.clientHeight });
    });
    ro.observe(el);
    setDims({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  const positions = useForceLayout(graph.nodes, graph.edges, dims.w, dims.h);

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8 flex flex-col">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <Link href={`/projects/${id}`} className="text-slate-400 hover:text-slate-300 text-sm">← Project</Link>
              <h1 className="text-2xl font-bold text-white mt-1">Knowledge Graph</h1>
              <p className="text-slate-400 text-sm mt-0.5">
                {graph.nodes.length} entities · {graph.edges.length} relations
              </p>
            </div>
            {/* Legend */}
            <div className="flex flex-wrap gap-2">
              {Object.entries(DOMAIN_COLORS).map(([domain, color]) => (
                <span key={domain} className="flex items-center gap-1 text-xs text-slate-300">
                  <span className="inline-block w-3 h-3 rounded-full" style={{ background: color }} />
                  {domain.replace("_", " ")}
                </span>
              ))}
            </div>
          </div>

          <div className="flex gap-4 flex-1">
            {/* SVG canvas */}
            <div ref={containerRef} className="flex-1 bg-surface-2 border border-surface-3 rounded-xl overflow-hidden" style={{ minHeight: 480 }}>
              {loading ? (
                <div className="flex items-center justify-center h-full text-slate-400">Loading graph…</div>
              ) : graph.nodes.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-2">
                  <p>No entities yet.</p>
                  <p className="text-sm">Run a research workflow to populate the knowledge graph.</p>
                </div>
              ) : (
                <svg width={dims.w} height={dims.h}>
                  <defs>
                    <marker id="arrow" markerWidth="6" markerHeight="6" refX="6" refY="3" orient="auto">
                      <path d="M0,0 L0,6 L6,3 z" fill="#475569" />
                    </marker>
                  </defs>
                  {/* Edges */}
                  {graph.edges.map((e) => {
                    const s = positions[e.source];
                    const t = positions[e.target];
                    if (!s || !t) return null;
                    return (
                      <g key={e.id}>
                        <line
                          x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                          stroke="#334155"
                          strokeWidth={1.5}
                          markerEnd="url(#arrow)"
                        />
                        <text
                          x={(s.x + t.x) / 2}
                          y={(s.y + t.y) / 2 - 4}
                          fill="#64748b"
                          fontSize={9}
                          textAnchor="middle"
                        >
                          {e.relation_type.replace("_", " ")}
                        </text>
                      </g>
                    );
                  })}
                  {/* Nodes */}
                  {graph.nodes.map((n) => {
                    const p = positions[n.id];
                    if (!p) return null;
                    const color = domainColor(n.domain);
                    const isSelected = selected?.id === n.id;
                    return (
                      <g
                        key={n.id}
                        transform={`translate(${p.x},${p.y})`}
                        style={{ cursor: "pointer" }}
                        onClick={() => setSelected(isSelected ? null : n)}
                      >
                        <circle
                          r={isSelected ? 12 : 8}
                          fill={color}
                          opacity={0.9}
                          stroke={isSelected ? "#fff" : "transparent"}
                          strokeWidth={2}
                        />
                        <text
                          y={-14}
                          fill="#e2e8f0"
                          fontSize={10}
                          textAnchor="middle"
                          style={{ pointerEvents: "none", userSelect: "none" }}
                        >
                          {n.name.length > 20 ? n.name.slice(0, 18) + "…" : n.name}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              )}
            </div>

            {/* Detail panel */}
            {selected && (
              <div className="w-64 bg-surface-2 border border-surface-3 rounded-xl p-4 flex-shrink-0">
                <button
                  onClick={() => setSelected(null)}
                  className="text-slate-400 hover:text-slate-200 text-xs mb-3 float-right"
                >✕</button>
                <h3 className="text-white font-semibold text-sm mb-1">{selected.name}</h3>
                <div className="flex gap-1 mb-3 flex-wrap">
                  <span className="text-xs px-2 py-0.5 rounded-full text-white" style={{ background: domainColor(selected.domain) }}>
                    {selected.domain}
                  </span>
                  <span className="text-xs bg-surface-3 text-slate-300 px-2 py-0.5 rounded-full">
                    {selected.entity_type}
                  </span>
                </div>
                {selected.description && (
                  <p className="text-slate-400 text-xs leading-relaxed mb-3">{selected.description}</p>
                )}
                <p className="text-slate-500 text-xs">Confidence: {(selected.confidence * 100).toFixed(0)}%</p>
                {selected.source_hypothesis_id && (
                  <p className="text-slate-500 text-xs mt-1">
                    Source: hypothesis <span className="font-mono">{selected.source_hypothesis_id.slice(0, 8)}…</span>
                  </p>
                )}
                <div className="mt-3 border-t border-surface-3 pt-3">
                  <p className="text-slate-500 text-xs font-medium mb-1">Connected via:</p>
                  {graph.edges
                    .filter((e) => e.source === selected.id || e.target === selected.id)
                    .map((e) => {
                      const other = graph.nodes.find((n) => n.id === (e.source === selected.id ? e.target : e.source));
                      return other ? (
                        <button
                          key={e.id}
                          onClick={() => setSelected(other)}
                          className="block text-xs text-primary-400 hover:text-primary-300 mt-1 text-left"
                        >
                          {e.relation_type.replace("_", " ")} → {other.name}
                        </button>
                      ) : null;
                    })}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
