"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import AuthGuard from "@/components/layout/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import api from "@/lib/api";
import type { SimulationOut, SimulationVariantIn } from "@/types";
import Link from "next/link";
import clsx from "clsx";

const SIM_TYPES = [
  { value: "agent_sweep",      label: "Agent Sweep",      desc: "Compare multiple agents on the same question" },
  { value: "parameter_sweep",  label: "Parameter Sweep",  desc: "Vary workflow flags (debate, critique, contradiction)" },
  { value: "stability_test",   label: "Stability Test",   desc: "Repeat the same config N times to measure variance" },
];

const AGENTS = ["math_research_agent", "llm_agent"];

const verdictStyle: Record<string, string> = {
  strong:   "text-green-400",
  moderate: "text-yellow-400",
  weak:     "text-red-400",
};

const statusBadge: Record<string, string> = {
  pending:   "bg-slate-700 text-slate-300",
  running:   "bg-yellow-900 text-yellow-300",
  completed: "bg-green-900 text-green-300",
  failed:    "bg-red-900 text-red-300",
};

function emptyVariant(): SimulationVariantIn {
  return { name: "", agent_name: "math_research_agent", enable_debate: false, enable_critique: false, enable_contradiction_check: false };
}

export default function SimulationsPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [simulations, setSimulations] = useState<SimulationOut[]>([]);
  const [creating, setCreating] = useState(false);
  const [running, setRunning] = useState(false);
  const [selected, setSelected] = useState<SimulationOut | null>(null);

  const [simType, setSimType] = useState<string>("agent_sweep");
  const [question, setQuestion] = useState("");
  const [variants, setVariants] = useState<SimulationVariantIn[]>([emptyVariant()]);
  const [runsPerVariant, setRunsPerVariant] = useState(1);

  async function load() {
    const r = await api.get(`/projects/${projectId}/simulations`);
    setSimulations(r.data);
  }

  useEffect(() => { load(); }, [projectId]);

  function addVariant() {
    setVariants((prev) => [...prev, emptyVariant()]);
  }

  function removeVariant(i: number) {
    setVariants((prev) => prev.filter((_, idx) => idx !== i));
  }

  function updateVariant(i: number, patch: Partial<SimulationVariantIn>) {
    setVariants((prev) => prev.map((v, idx) => idx === i ? { ...v, ...patch } : v));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setRunning(true);
    try {
      const r = await api.post(`/projects/${projectId}/simulations`, {
        simulation_type: simType,
        question,
        variants: variants.filter((v) => v.name.trim() && v.agent_name),
        runs_per_variant: runsPerVariant,
      });
      setSimulations((prev) => [r.data, ...prev]);
      setSelected(r.data);
      setCreating(false);
      setQuestion("");
      setVariants([emptyVariant()]);
    } finally {
      setRunning(false);
    }
  }

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Link href={`/projects/${projectId}`} className="text-slate-400 hover:text-slate-300 text-sm">← Project</Link>
              <h1 className="text-2xl font-bold text-white">Simulations</h1>
            </div>
            <button onClick={() => setCreating(!creating)} className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
              {creating ? "Cancel" : "New Simulation"}
            </button>
          </div>

          {creating && (
            <form onSubmit={handleSubmit} className="bg-surface-2 border border-surface-3 rounded-xl p-6 mb-6 space-y-5">
              {/* Type picker */}
              <div>
                <p className="text-xs text-slate-400 mb-2 uppercase tracking-wide">Simulation type</p>
                <div className="grid grid-cols-3 gap-3">
                  {SIM_TYPES.map((t) => (
                    <button
                      key={t.value}
                      type="button"
                      onClick={() => setSimType(t.value)}
                      className={clsx(
                        "rounded-lg border p-3 text-left transition-colors",
                        simType === t.value
                          ? "border-primary-500 bg-primary-900/30 text-white"
                          : "border-surface-3 text-slate-400 hover:border-slate-500"
                      )}
                    >
                      <p className="text-sm font-medium">{t.label}</p>
                      <p className="text-xs mt-0.5 opacity-70">{t.desc}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Question */}
              <textarea
                required
                placeholder="Research question to simulate…"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                rows={2}
                className="w-full bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
              />

              {/* Variants */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-slate-400 uppercase tracking-wide">Variants</p>
                  <button type="button" onClick={addVariant} className="text-xs text-primary-400 hover:text-primary-300">+ Add variant</button>
                </div>
                <div className="space-y-2">
                  {variants.map((v, i) => (
                    <div key={i} className="bg-surface-3 rounded-lg p-3 flex flex-wrap items-center gap-3">
                      <input
                        required
                        placeholder="Variant name"
                        value={v.name}
                        onChange={(e) => updateVariant(i, { name: e.target.value })}
                        className="bg-surface-2 border border-slate-600 rounded px-2 py-1 text-sm text-white w-40 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      />
                      <select
                        value={v.agent_name}
                        onChange={(e) => updateVariant(i, { agent_name: e.target.value })}
                        className="bg-surface-2 border border-slate-600 rounded px-2 py-1 text-sm text-white focus:outline-none focus:ring-1 focus:ring-primary-500"
                      >
                        {AGENTS.map((a) => <option key={a} value={a}>{a}</option>)}
                      </select>
                      <label className="flex items-center gap-1 text-xs text-slate-400 cursor-pointer">
                        <input type="checkbox" checked={v.enable_debate} onChange={(e) => updateVariant(i, { enable_debate: e.target.checked })} className="rounded" />
                        Debate
                      </label>
                      <label className="flex items-center gap-1 text-xs text-slate-400 cursor-pointer">
                        <input type="checkbox" checked={v.enable_critique} onChange={(e) => updateVariant(i, { enable_critique: e.target.checked })} className="rounded" />
                        Critique
                      </label>
                      <label className="flex items-center gap-1 text-xs text-slate-400 cursor-pointer">
                        <input type="checkbox" checked={v.enable_contradiction_check} onChange={(e) => updateVariant(i, { enable_contradiction_check: e.target.checked })} className="rounded" />
                        Contradiction
                      </label>
                      {variants.length > 1 && (
                        <button type="button" onClick={() => removeVariant(i)} className="ml-auto text-xs text-red-400 hover:text-red-300">Remove</button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Runs per variant (stability_test only) */}
              {simType === "stability_test" && (
                <div className="flex items-center gap-3">
                  <label className="text-xs text-slate-400">Runs per variant</label>
                  <input
                    type="number" min={1} max={10}
                    value={runsPerVariant}
                    onChange={(e) => setRunsPerVariant(Number(e.target.value))}
                    className="w-20 bg-surface-3 border border-slate-600 rounded px-2 py-1 text-sm text-white focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              )}

              <button
                type="submit"
                disabled={running}
                className="bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                {running ? "Running simulation…" : "Run Simulation"}
              </button>
            </form>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* List */}
            <div className="space-y-3">
              {simulations.map((sim) => (
                <button
                  key={sim.id}
                  onClick={() => setSelected(sim)}
                  className="w-full text-left bg-surface-2 border border-surface-3 hover:border-primary-500 rounded-xl p-5 transition-colors"
                >
                  <div className="flex items-start justify-between mb-1">
                    <p className="text-sm font-semibold text-white truncate max-w-xs">{sim.question}</p>
                    <span className={clsx("text-xs px-2 py-0.5 rounded ml-2 shrink-0", statusBadge[sim.status])}>{sim.status}</span>
                  </div>
                  <p className="text-xs text-slate-500">{sim.simulation_type.replace(/_/g, " ")} · {sim.variant_results.length} run{sim.variant_results.length !== 1 ? "s" : ""}</p>
                  {sim.best_variant && (
                    <p className="text-xs text-green-400 mt-1">Best: {sim.best_variant}</p>
                  )}
                </button>
              ))}
              {simulations.length === 0 && <p className="text-slate-500 text-center py-12">No simulations yet.</p>}
            </div>

            {/* Detail */}
            {selected && (
              <div className="bg-surface-2 border border-surface-3 rounded-xl p-6">
                <div className="flex items-start justify-between mb-1">
                  <h3 className="text-base font-semibold text-white">{selected.question}</h3>
                  <span className={clsx("text-xs px-2 py-0.5 rounded ml-2 shrink-0", statusBadge[selected.status])}>{selected.status}</span>
                </div>
                <p className="text-xs text-slate-500 mb-4">{selected.simulation_type.replace(/_/g, " ")} · {new Date(selected.created_at).toLocaleString()}</p>

                {selected.summary && Object.keys(selected.summary).length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs text-slate-400 uppercase tracking-wide mb-2">Summary</p>
                    <div className="space-y-1">
                      {Object.entries(selected.summary).map(([vname, stats]: [string, any]) => (
                        <div key={vname} className="flex items-center gap-3">
                          <span className={clsx("text-xs w-2 h-2 rounded-full inline-block", vname === selected.best_variant ? "bg-green-400" : "bg-slate-500")} />
                          <span className="text-sm text-white w-40 truncate">{vname}</span>
                          <div className="flex-1 bg-slate-700 rounded-full h-1.5">
                            <div className="bg-primary-500 h-1.5 rounded-full" style={{ width: `${((stats.mean || 0) * 100).toFixed(0)}%` }} />
                          </div>
                          <span className="text-xs text-slate-300 w-24 text-right">
                            {((stats.mean || 0) * 100).toFixed(0)}%
                            {stats.std > 0 && <span className="text-slate-500"> ±{(stats.std * 100).toFixed(0)}</span>}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <p className="text-xs text-slate-400 uppercase tracking-wide mb-2">Variant runs ({selected.variant_results.length})</p>
                <div className="space-y-2 max-h-72 overflow-y-auto">
                  {selected.variant_results.map((vr) => (
                    <div key={vr.id} className="bg-surface-3 rounded-lg p-3 flex items-center justify-between">
                      <div>
                        <p className="text-sm text-white">{vr.variant_name}</p>
                        <p className="text-xs text-slate-500">{vr.agent_name}{selected.simulation_type === "stability_test" ? ` · run ${vr.run_index + 1}` : ""}</p>
                      </div>
                      <div className="text-right">
                        {vr.evaluation_score !== null ? (
                          <>
                            <p className={clsx("text-sm font-medium", verdictStyle[vr.verdict ?? "weak"])}>
                              {((vr.evaluation_score ?? 0) * 100).toFixed(0)}%
                            </p>
                            <p className="text-xs text-slate-500 capitalize">{vr.verdict}</p>
                          </>
                        ) : (
                          <p className="text-xs text-slate-500">—</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {selected.status === "failed" && selected.summary?.error && (
                  <p className="text-xs text-red-400 mt-3">{selected.summary.error as string}</p>
                )}
              </div>
            )}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
