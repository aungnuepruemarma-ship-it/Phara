"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import AuthGuard from "@/components/layout/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import api from "@/lib/api";
import type { SimulationOut, SimulationVariantIn } from "@/types";
import Link from "next/link";
import clsx from "clsx";

// ---------------------------------------------------------------------------
// Simulation type catalog — 15 types in 3 groups
// ---------------------------------------------------------------------------
const SIM_GROUPS = [
  {
    label: "Sweep",
    types: [
      { value: "agent_sweep",           label: "Agent Sweep",           desc: "Compare multiple agents on the same question" },
      { value: "parameter_sweep",       label: "Parameter Sweep",       desc: "Vary workflow flags (debate, critique, contradiction)" },
      { value: "stability_test",        label: "Stability Test",        desc: "Repeat same config N times to measure variance" },
      { value: "hypothesis_sweep",      label: "Hypothesis Sweep",      desc: "Compare different hypothesis framings" },
      { value: "debate_simulation",     label: "Debate Simulation",     desc: "Different agent teams argue for/against" },
      { value: "cross_domain_transfer", label: "Cross-Domain Transfer", desc: "Test whether patterns from one field help another" },
    ],
  },
  {
    label: "Ablation",
    types: [
      { value: "retrieval_ablation", label: "Retrieval Ablation", desc: "Measure contribution of paper retrieval" },
      { value: "memory_ablation",    label: "Memory Ablation",    desc: "Disable long-term memory to quantify its value" },
      { value: "kg_ablation",        label: "KG Ablation",        desc: "Remove knowledge graph reasoning" },
      { value: "tool_ablation",      label: "Tool Ablation",      desc: "Disable tools to measure their impact" },
    ],
  },
  {
    label: "Advanced",
    types: [
      { value: "adversarial_simulation", label: "Adversarial",       desc: "Inject misleading evidence and test robustness" },
      { value: "time_evolution",         label: "Time Evolution",     desc: "Observe how conclusions change with new information" },
      { value: "human_loop",             label: "Human-in-the-Loop",  desc: "Compare agent-only vs human-reviewed workflows" },
      { value: "cost_optimization",      label: "Cost Optimization",  desc: "Trade off quality vs compute vs latency" },
      { value: "scaling_simulation",     label: "Scaling",            desc: "Vary retrieval depth to find bottlenecks" },
    ],
  },
];

const ALL_TYPES = SIM_GROUPS.flatMap((g) => g.types);

const AGENTS = ["math_research_agent", "llm_agent", "physics_agent", "biology_agent", "cs_agent", "ai_research_agent"];

const ABLATION_SIM_TYPES = new Set(["retrieval_ablation", "memory_ablation", "kg_ablation", "tool_ablation"]);
const ADVERSARIAL_TYPES = new Set(["adversarial_simulation"]);
const SCALING_TYPES = new Set(["scaling_simulation"]);

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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function emptyVariant(): SimulationVariantIn {
  return {
    name: "",
    agent_name: "math_research_agent",
    enable_debate: false,
    enable_critique: false,
    enable_contradiction_check: false,
    ablate_retrieval: false,
    ablate_memory: false,
    ablate_kg: false,
    ablate_tools: false,
    adversarial_context: [],
    retrieval_top_k: null,
  };
}

function AblationBadge({ label }: { label: string }) {
  return (
    <span className="text-xs px-1.5 py-0.5 rounded bg-red-900/40 border border-red-800 text-red-300">{label}</span>
  );
}

// ---------------------------------------------------------------------------
// FullStatePanel — expandable simulation memory viewer
// ---------------------------------------------------------------------------
function FullStatePanel({ state }: { state: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  const flags = (state.ablation_flags as Record<string, unknown>) || {};
  const activeFlags = Object.entries(flags).filter(([, v]) => v === true).map(([k]) => k.replace("ablate_", ""));

  return (
    <div className="mt-2 border-t border-slate-700 pt-2">
      <div className="flex items-center justify-between">
        <div className="flex flex-wrap gap-1">
          {activeFlags.map((f) => <AblationBadge key={f} label={`-${f}`} />)}
          {typeof state.retrieved_chunk_count === "number" && (
            <span className="text-xs text-slate-500">{state.retrieved_chunk_count} chunks</span>
          )}
          {typeof state.contradiction_count === "number" && state.contradiction_count > 0 && (
            <span className="text-xs text-amber-500">{state.contradiction_count} contradictions</span>
          )}
          {typeof state.kg_entities_created === "object" && Array.isArray(state.kg_entities_created) && state.kg_entities_created.length > 0 && (
            <span className="text-xs text-cyan-500">{state.kg_entities_created.length} KG entities</span>
          )}
        </div>
        <button onClick={() => setOpen(!open)} className="text-xs text-slate-500 hover:text-slate-300">{open ? "hide state" : "show state"}</button>
      </div>
      {open && (
        <pre className="mt-2 text-xs text-slate-400 overflow-x-auto whitespace-pre-wrap max-h-48">
          {JSON.stringify(state, null, 2).slice(0, 3000)}
        </pre>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function SimulationsPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [simulations, setSimulations] = useState<SimulationOut[]>([]);
  const [creating, setCreating] = useState(false);
  const [running, setRunning] = useState(false);
  const [selected, setSelected] = useState<SimulationOut | null>(null);
  const [knowledge, setKnowledge] = useState<{ text: string; source_simulation_id: string; score: number }[]>([]);
  const [showKnowledge, setShowKnowledge] = useState(false);

  const [simType, setSimType] = useState<string>("agent_sweep");
  const [question, setQuestion] = useState("");
  const [variants, setVariants] = useState<SimulationVariantIn[]>([emptyVariant()]);
  const [runsPerVariant, setRunsPerVariant] = useState(1);
  const [adversarialText, setAdversarialText] = useState("");

  async function load() {
    const r = await api.get(`/projects/${projectId}/simulations`);
    setSimulations(r.data);
  }

  async function loadKnowledge() {
    try {
      const r = await api.get(`/projects/${projectId}/simulation-knowledge`);
      setKnowledge(r.data);
    } catch {
      setKnowledge([]);
    }
  }

  useEffect(() => {
    load();
    loadKnowledge();
  }, [projectId]);

  function addVariant() {
    setVariants((prev) => [...prev, emptyVariant()]);
  }

  function removeVariant(i: number) {
    setVariants((prev) => prev.filter((_, idx) => idx !== i));
  }

  function updateVariant(i: number, patch: Partial<SimulationVariantIn>) {
    setVariants((prev) => prev.map((v, idx) => idx === i ? { ...v, ...patch } : v));
  }

  // Auto-configure ablation variants when switching to an ablation type
  function handleTypeChange(newType: string) {
    setSimType(newType);
    if (ABLATION_SIM_TYPES.has(newType) && variants.length === 1 && !variants[0].name) {
      const component = newType.replace("_ablation", "");
      const withFlag = `with_${component}`;
      const withoutFlag = `no_${component}`;
      const ablationKey = `ablate_${component}` as keyof SimulationVariantIn;
      setVariants([
        { ...emptyVariant(), name: withFlag },
        { ...emptyVariant(), name: withoutFlag, [ablationKey]: true },
      ]);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setRunning(true);
    try {
      const preparedVariants = variants
        .filter((v) => v.name.trim() && v.agent_name)
        .map((v) => ({
          ...v,
          adversarial_context: ADVERSARIAL_TYPES.has(simType) && adversarialText.trim()
            ? adversarialText.split("\n").filter(Boolean)
            : [],
        }));

      const r = await api.post(`/projects/${projectId}/simulations`, {
        simulation_type: simType,
        question,
        variants: preparedVariants,
        runs_per_variant: runsPerVariant,
      });
      setSimulations((prev) => [r.data, ...prev]);
      setSelected(r.data);
      setCreating(false);
      setQuestion("");
      setVariants([emptyVariant()]);
      setAdversarialText("");
      await loadKnowledge();
    } finally {
      setRunning(false);
    }
  }

  const selectedType = ALL_TYPES.find((t) => t.value === simType);

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8 max-w-6xl">
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
                {SIM_GROUPS.map((group) => (
                  <div key={group.label} className="mb-3">
                    <p className="text-xs text-slate-500 uppercase tracking-wide mb-1.5">{group.label}</p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {group.types.map((t) => (
                        <button
                          key={t.value}
                          type="button"
                          onClick={() => handleTypeChange(t.value)}
                          className={clsx(
                            "rounded-lg border p-2.5 text-left transition-colors",
                            simType === t.value
                              ? "border-primary-500 bg-primary-900/30 text-white"
                              : "border-surface-3 text-slate-400 hover:border-slate-500"
                          )}
                        >
                          <p className="text-xs font-medium leading-snug">{t.label}</p>
                          <p className="text-xs mt-0.5 opacity-60 leading-snug">{t.desc}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {selectedType && (
                <p className="text-xs text-primary-400 -mt-2">{selectedType.label}: {selectedType.desc}</p>
              )}

              {/* Question */}
              <textarea
                required
                placeholder="Research question to simulate…"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                rows={2}
                className="w-full bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
              />

              {/* Adversarial context (adversarial_simulation only) */}
              {ADVERSARIAL_TYPES.has(simType) && (
                <div>
                  <label className="block text-xs text-slate-400 mb-1 uppercase tracking-wide">Adversarial chunks (one per line)</label>
                  <textarea
                    placeholder={"Misleading statement 1\nMisleading statement 2"}
                    value={adversarialText}
                    onChange={(e) => setAdversarialText(e.target.value)}
                    rows={3}
                    className="w-full bg-surface-3 border border-amber-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-amber-600 resize-none text-sm"
                  />
                </div>
              )}

              {/* Variants */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-slate-400 uppercase tracking-wide">Variants</p>
                  <button type="button" onClick={addVariant} className="text-xs text-primary-400 hover:text-primary-300">+ Add variant</button>
                </div>
                <div className="space-y-3">
                  {variants.map((v, i) => (
                    <div key={i} className="bg-surface-3 rounded-lg p-3 space-y-2">
                      {/* Row 1: name + agent + workflow flags */}
                      <div className="flex flex-wrap items-center gap-2">
                        <input
                          required
                          placeholder="Variant name"
                          value={v.name}
                          onChange={(e) => updateVariant(i, { name: e.target.value })}
                          className="bg-surface-2 border border-slate-600 rounded px-2 py-1 text-sm text-white w-36 focus:outline-none focus:ring-1 focus:ring-primary-500"
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

                      {/* Row 2: ablation flags */}
                      <div className="flex flex-wrap gap-3 pt-1 border-t border-slate-700">
                        <span className="text-xs text-slate-600 self-center">Ablate:</span>
                        {(["ablate_retrieval", "ablate_memory", "ablate_kg", "ablate_tools"] as const).map((flag) => (
                          <label key={flag} className="flex items-center gap-1 text-xs text-slate-400 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={!!v[flag]}
                              onChange={(e) => updateVariant(i, { [flag]: e.target.checked })}
                              className="rounded accent-red-500"
                            />
                            {flag.replace("ablate_", "")}
                          </label>
                        ))}
                        {SCALING_TYPES.has(simType) && (
                          <label className="flex items-center gap-1 text-xs text-slate-400">
                            top_k:
                            <input
                              type="number"
                              min={1} max={50}
                              value={v.retrieval_top_k ?? ""}
                              onChange={(e) => updateVariant(i, { retrieval_top_k: e.target.value ? Number(e.target.value) : null })}
                              placeholder="default"
                              className="w-16 bg-surface-2 border border-slate-600 rounded px-1.5 py-0.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-primary-500"
                            />
                          </label>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Runs per variant */}
              {(simType === "stability_test" || simType === "scaling_simulation") && (
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
                          <span className={clsx("w-2 h-2 rounded-full inline-block shrink-0", vname === selected.best_variant ? "bg-green-400" : "bg-slate-500")} />
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
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {selected.variant_results.map((vr) => (
                    <div key={vr.id} className="bg-surface-3 rounded-lg p-3">
                      <div className="flex items-center justify-between">
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
                      {vr.full_state && Object.keys(vr.full_state).length > 0 && (
                        <FullStatePanel state={vr.full_state} />
                      )}
                    </div>
                  ))}
                </div>

                {selected.status === "failed" && selected.summary?.error && (
                  <p className="text-xs text-red-400 mt-3">{selected.summary.error as string}</p>
                )}
              </div>
            )}
          </div>

          {/* Simulation Knowledge Base */}
          <div className="mt-8 bg-surface-2 border border-surface-3 rounded-xl p-6">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-base font-semibold text-white">Simulation Knowledge Base</h2>
                <p className="text-xs text-slate-500 mt-0.5">Lessons extracted from past simulations — surfaced in future research runs</p>
              </div>
              <button
                onClick={() => setShowKnowledge(!showKnowledge)}
                className="text-xs text-slate-400 hover:text-slate-300"
              >
                {showKnowledge ? "hide" : `show (${knowledge.length})`}
              </button>
            </div>
            {showKnowledge && (
              knowledge.length === 0 ? (
                <p className="text-sm text-slate-500">No lessons yet. Run a simulation to generate knowledge.</p>
              ) : (
                <div className="space-y-2">
                  {knowledge.map((entry, i) => (
                    <div key={i} className="bg-surface-3 rounded-lg p-3 flex items-start gap-3">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary-500 mt-1.5 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-slate-200 leading-relaxed">{entry.text}</p>
                        <p className="text-xs text-slate-600 mt-1">sim {entry.source_simulation_id.slice(0, 8)}… · relevance {(entry.score * 100).toFixed(0)}%</p>
                      </div>
                    </div>
                  ))}
                </div>
              )
            )}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
