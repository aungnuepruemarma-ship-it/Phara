"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import AuthGuard from "@/components/layout/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import api from "@/lib/api";
import type { TrackingRun } from "@/types";
import Link from "next/link";
import clsx from "clsx";

const statusColor: Record<string, string> = {
  FINISHED: "bg-green-900 text-green-300",
  RUNNING: "bg-yellow-900 text-yellow-300",
  FAILED: "bg-red-900 text-red-300",
  KILLED: "bg-red-900 text-red-300",
};

function MetricBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-surface-3 rounded-full overflow-hidden">
        <div className="h-full bg-primary-500 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-400 w-8 text-right">{value.toFixed(2)}</span>
    </div>
  );
}

export default function TrackingPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [runs, setRuns] = useState<TrackingRun[]>([]);
  const [selected, setSelected] = useState<TrackingRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get(`/projects/${projectId}/tracking`)
      .then((r) => setRuns(r.data.runs))
      .catch(() => setError("Failed to load tracking data."))
      .finally(() => setLoading(false));
  }, [projectId]);

  const maxConfidence = Math.max(...runs.map((r) => r.metrics.confidence_score ?? 0), 1);

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8">
          <div className="flex items-center gap-3 mb-6">
            <Link href={`/projects/${projectId}`} className="text-slate-400 hover:text-slate-300 text-sm">← Project</Link>
            <h1 className="text-2xl font-bold text-white">MLflow Tracking</h1>
          </div>

          {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
          {loading && <p className="text-slate-400">Loading runs…</p>}

          {!loading && runs.length === 0 && (
            <div className="bg-surface-2 border border-surface-3 rounded-xl p-12 text-center">
              <p className="text-slate-400">No tracked runs yet.</p>
              <p className="text-slate-500 text-sm mt-2">Run a research workflow to start tracking.</p>
            </div>
          )}

          {runs.length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Run list */}
              <div className="lg:col-span-1 space-y-2">
                <p className="text-xs text-slate-500 font-medium uppercase tracking-wide mb-3">{runs.length} runs</p>
                {runs.map((run) => (
                  <button
                    key={run.run_id}
                    onClick={() => setSelected(run)}
                    className={clsx(
                      "w-full text-left rounded-xl p-4 border transition-colors",
                      selected?.run_id === run.run_id
                        ? "border-primary-500 bg-surface-2"
                        : "border-surface-3 bg-surface-2 hover:border-slate-500"
                    )}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-xs text-slate-400">{run.run_id.slice(0, 8)}</span>
                      {run.status && (
                        <span className={clsx("text-xs px-1.5 py-0.5 rounded", statusColor[run.status] ?? "bg-surface-3 text-slate-400")}>
                          {run.status}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-white truncate">{run.params.question?.slice(0, 60) ?? "—"}</p>
                    <p className="text-xs text-slate-500 mt-1">
                      {run.params.agent_name ?? "—"}
                      {run.metrics.confidence_score != null && ` · ${(run.metrics.confidence_score * 100).toFixed(0)}% conf`}
                    </p>
                  </button>
                ))}
              </div>

              {/* Run detail */}
              <div className="lg:col-span-2">
                {selected ? (
                  <div className="bg-surface-2 border border-surface-3 rounded-xl p-6 space-y-6">
                    <div>
                      <div className="flex items-center gap-3 mb-1">
                        <span className="font-mono text-sm text-slate-400">{selected.run_id}</span>
                        {selected.status && (
                          <span className={clsx("text-xs px-2 py-0.5 rounded", statusColor[selected.status] ?? "bg-surface-3 text-slate-400")}>
                            {selected.status}
                          </span>
                        )}
                      </div>
                      {selected.start_time && (
                        <p className="text-xs text-slate-500">{selected.start_time}</p>
                      )}
                    </div>

                    <div>
                      <h3 className="text-sm font-medium text-slate-300 mb-2">Parameters</h3>
                      <div className="space-y-1">
                        {Object.entries(selected.params).map(([k, v]) => (
                          <div key={k} className="flex gap-2 text-sm">
                            <span className="text-slate-400 font-mono w-36 shrink-0">{k}</span>
                            <span className="text-white break-all">{String(v)}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h3 className="text-sm font-medium text-slate-300 mb-3">Metrics</h3>
                      <div className="space-y-2">
                        <div>
                          <p className="text-xs text-slate-400 mb-1">Confidence Score</p>
                          <MetricBar value={selected.metrics.confidence_score ?? 0} max={1} />
                        </div>
                        {Object.entries(selected.metrics)
                          .filter(([k]) => k !== "confidence_score")
                          .map(([k, v]) => (
                            <div key={k} className="flex justify-between text-sm">
                              <span className="text-slate-400 font-mono">{k}</span>
                              <span className="text-white">{String(v)}</span>
                            </div>
                          ))}
                      </div>
                    </div>

                    {Object.keys(selected.tags).length > 0 && (
                      <div>
                        <h3 className="text-sm font-medium text-slate-300 mb-2">Tags</h3>
                        <div className="space-y-1">
                          {Object.entries(selected.tags).map(([k, v]) => (
                            <div key={k} className="flex gap-2 text-sm">
                              <span className="text-slate-400 font-mono w-36 shrink-0">{k}</span>
                              <span className="text-white break-all">{String(v).slice(0, 200)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-surface-2 border border-surface-3 rounded-xl p-12 text-center">
                    <p className="text-slate-400 text-sm">Select a run to inspect</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </main>
      </div>
    </AuthGuard>
  );
}
