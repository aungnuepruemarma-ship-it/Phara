"use client";
import { useEffect, useState } from "react";
import AuthGuard from "@/components/layout/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import api from "@/lib/api";
import type { Project, Experiment, WorkflowResult, DebateEntry, ContradictionItem, ToolSpec, ToolResult } from "@/types";
import ReactMarkdown from "react-markdown";

const CATEGORY_ORDER = ["live_data", "research", "memory", "analysis", "utility"];

const CATEGORY_LABELS: Record<string, string> = {
  live_data: "Live Web & Data",
  research: "Research",
  memory: "Memory",
  analysis: "Analysis",
  utility: "Utility",
};

function ToolResultCard({ result }: { result: ToolResult }) {
  const [open, setOpen] = useState(false);
  const preview = result.output
    ? JSON.stringify(result.output).slice(0, 120) + (JSON.stringify(result.output).length > 120 ? "…" : "")
    : "";
  return (
    <div className="bg-surface-3 rounded-lg p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${result.success ? "bg-green-400" : "bg-red-400"}`} />
          <span className="text-sm font-medium text-white">{result.tool_name}</span>
          <span className="text-xs text-slate-500">{result.elapsed_ms.toFixed(0)}ms</span>
        </div>
        {result.output && (
          <button onClick={() => setOpen(!open)} className="text-xs text-slate-400 hover:text-white">{open ? "hide" : "show"}</button>
        )}
      </div>
      {result.error && <p className="text-xs text-red-400 mt-1">{result.error}</p>}
      {open && result.output && (
        <pre className="mt-2 text-xs text-slate-300 overflow-x-auto whitespace-pre-wrap">
          {JSON.stringify(result.output, null, 2).slice(0, 2000)}
        </pre>
      )}
      {!open && preview && <p className="text-xs text-slate-500 mt-1 truncate">{preview}</p>}
    </div>
  );
}

const severityColor: Record<string, string> = {
  high: "border-red-700 text-red-300",
  medium: "border-amber-700 text-amber-300",
  low: "border-slate-600 text-slate-400",
};

function ContradictionCard({ item, index }: { item: ContradictionItem; index: number }) {
  return (
    <div className={`border rounded-xl p-4 ${severityColor[item.severity] || severityColor.low}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold uppercase tracking-wide">Contradiction {index + 1}</span>
        <span className={`text-xs px-2 py-0.5 rounded border ${severityColor[item.severity]}`}>{item.severity}</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        <div className="bg-surface-3 rounded-lg p-3">
          <p className="text-xs text-slate-500 mb-1">Source [{item.source_a}]</p>
          <p className="text-slate-200">{item.claim_a}</p>
        </div>
        <div className="bg-surface-3 rounded-lg p-3">
          <p className="text-xs text-slate-500 mb-1">Source [{item.source_b}]</p>
          <p className="text-slate-200">{item.claim_b}</p>
        </div>
      </div>
      {item.explanation && <p className="text-xs text-slate-400 mt-2">{item.explanation}</p>}
    </div>
  );
}

function DebateCard({ entry, label }: { entry: DebateEntry; label: string }) {
  const [open, setOpen] = useState(false);
  const roleColor =
    entry.role === "pro" ? "border-emerald-700 bg-emerald-950/40" :
    entry.role === "con" ? "border-red-700 bg-red-950/40" :
    "border-amber-700 bg-amber-950/40";
  return (
    <div className={`border rounded-xl p-4 ${roleColor}`}>
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</span>
          <p className="text-slate-200 text-sm mt-1">{entry.hypothesis}</p>
        </div>
        <div className="flex items-center gap-3 ml-4 shrink-0">
          <span className="text-xs text-slate-400">{(entry.confidence * 100).toFixed(0)}%</span>
          <button onClick={() => setOpen(!open)} className="text-xs text-slate-400 hover:text-white transition-colors">
            {open ? "hide" : "reasoning"}
          </button>
        </div>
      </div>
      {open && (
        <div className="mt-3 pt-3 border-t border-slate-700 prose prose-invert prose-sm max-w-none">
          <ReactMarkdown>{entry.reasoning}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}

export default function ResearchPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [agents, setAgents] = useState<{ name: string; description: string }[]>([]);
  const [availableTools, setAvailableTools] = useState<ToolSpec[]>([]);
  const [showTools, setShowTools] = useState(false);
  const [form, setForm] = useState({
    question: "",
    project_id: "",
    experiment_id: "",
    agent_name: "math_research_agent",
    enable_debate: false,
    enable_critique: false,
    enable_contradiction_check: false,
    enabled_tools: [] as string[],
    auto_tools: true,
  });
  const [result, setResult] = useState<WorkflowResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/projects").then((r) => setProjects(r.data)).catch(() => {});
    api.get("/research/agents").then((r) => setAgents(r.data)).catch(() => {});
    api.get("/tools").then((r) => setAvailableTools(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (form.project_id) {
      api.get(`/projects/${form.project_id}/experiments`).then((r) => setExperiments(r.data)).catch(() => {});
    } else {
      setExperiments([]);
    }
    setForm((f) => ({ ...f, experiment_id: "" }));
  }, [form.project_id]);

  async function handleRun(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setResult(null);
    setRunning(true);
    try {
      const r = await api.post("/research/run", form);
      setResult(r.data);
    } catch (err: unknown) {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Workflow failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8 max-w-4xl">
          <h1 className="text-2xl font-bold text-white mb-2">Research Workflow</h1>
          <p className="text-slate-400 text-sm mb-8">Ask a research question, retrieve relevant papers, and generate a hypothesis.</p>

          <form onSubmit={handleRun} className="bg-surface-2 border border-surface-3 rounded-xl p-6 space-y-4 mb-8">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Research Question</label>
              <textarea
                placeholder="What is the relationship between gradient descent convergence and loss landscape geometry?"
                value={form.question}
                onChange={(e) => setForm({ ...form, question: e.target.value })}
                required
                rows={3}
                className="w-full bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Project</label>
                <select value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })} required className="w-full bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500">
                  <option value="">Select…</option>
                  {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Experiment</label>
                <select value={form.experiment_id} onChange={(e) => setForm({ ...form, experiment_id: e.target.value })} className="w-full bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500">
                  <option value="">Auto-create from question</option>
                  {experiments.map((exp) => <option key={exp.id} value={exp.id}>{exp.title}</option>)}
                </select>
                {form.project_id && experiments.length === 0 && (
                  <p className="text-xs text-slate-500 mt-1">No experiments yet — a new one will be created automatically.</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Agent</label>
                <select value={form.agent_name} onChange={(e) => setForm({ ...form, agent_name: e.target.value })} className="w-full bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500">
                  {agents.map((a) => <option key={a.name} value={a.name}>{a.name}</option>)}
                </select>
              </div>
            </div>

            <div className="flex gap-6">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={form.enable_critique}
                  onChange={(e) => setForm({ ...form, enable_critique: e.target.checked })}
                  className="w-4 h-4 accent-primary-500"
                />
                <span className="text-sm text-slate-300">Enable Critique</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={form.enable_debate}
                  onChange={(e) => setForm({ ...form, enable_debate: e.target.checked })}
                  className="w-4 h-4 accent-primary-500"
                />
                <span className="text-sm text-slate-300">Enable Debate</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={form.enable_contradiction_check}
                  onChange={(e) => setForm({ ...form, enable_contradiction_check: e.target.checked })}
                  className="w-4 h-4 accent-primary-500"
                />
                <span className="text-sm text-slate-300">Detect Contradictions</span>
              </label>
            </div>

            {availableTools.length > 0 && (
              <div className="space-y-2">
                {/* Auto-select toggle */}
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={form.auto_tools}
                    onChange={(e) => setForm({ ...form, auto_tools: e.target.checked, enabled_tools: [] })}
                    className="w-4 h-4 accent-primary-500"
                  />
                  <span className="text-sm text-slate-300">Auto-select tools</span>
                  <span className="text-xs text-slate-500">— agents pick relevant data sources automatically</span>
                </label>

                {/* Manual tool picker (shown only when auto is off) */}
                {!form.auto_tools && (
                  <div>
                    <button
                      type="button"
                      onClick={() => setShowTools(!showTools)}
                      className="text-sm text-slate-400 hover:text-slate-300 flex items-center gap-1"
                    >
                      <span>{showTools ? "▾" : "▸"}</span>
                      Manual tools ({form.enabled_tools.length} selected)
                    </button>
                    {showTools && (
                      <div className="mt-3 space-y-4">
                        {CATEGORY_ORDER.map((cat) => {
                          const tools = availableTools.filter((t) => t.category === cat);
                          if (tools.length === 0) return null;
                          return (
                            <div key={cat}>
                              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                                {CATEGORY_LABELS[cat] ?? cat}
                              </p>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                {tools.map((tool) => (
                                  <label key={tool.name} className="flex items-start gap-2 cursor-pointer bg-surface-3 rounded-lg p-2.5 hover:bg-surface-2 transition-colors">
                                    <input
                                      type="checkbox"
                                      className="mt-0.5 accent-primary-500"
                                      checked={form.enabled_tools.includes(tool.name)}
                                      onChange={(e) => {
                                        const updated = e.target.checked
                                          ? [...form.enabled_tools, tool.name]
                                          : form.enabled_tools.filter((n) => n !== tool.name);
                                        setForm({ ...form, enabled_tools: updated });
                                      }}
                                    />
                                    <div>
                                      <p className="text-xs font-medium text-white">{tool.name}</p>
                                      <p className="text-xs text-slate-500">{tool.description.slice(0, 90)}{tool.description.length > 90 ? "…" : ""}</p>
                                    </div>
                                  </label>
                                ))}
                              </div>
                            </div>
                          );
                        })}
                        {form.enabled_tools.length > 0 && (
                          <button
                            type="button"
                            onClick={() => setForm({ ...form, enabled_tools: [] })}
                            className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                          >
                            Clear all
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {form.auto_tools && (
                  <p className="text-xs text-slate-500">
                    Tools such as Semantic Scholar, Wikipedia, arXiv, PubMed, and OpenAlex will be chosen based on your question.
                  </p>
                )}
              </div>
            )}

            {error && <p className="text-red-400 text-sm">{error}</p>}

            <button type="submit" disabled={running} className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2.5 rounded-lg font-medium transition-colors disabled:opacity-50">
              {running ? "Running workflow…" : "Run Research Workflow"}
            </button>
          </form>

          {result && (
            <div className="space-y-6">
              <div className="bg-surface-2 border border-primary-700 rounded-xl p-6">
                <h2 className="text-lg font-semibold text-white mb-1">Hypothesis</h2>
                <p className="text-xs text-slate-400 mb-4">
                  Agent: {result.hypothesis.agent_used} · {result.retrieved_paper_count} papers retrieved
                  {result.hypothesis.confidence_score !== null && ` · ${(result.hypothesis.confidence_score * 100).toFixed(0)}% confidence`}
                  {result.mlflow_run_id && <span className="ml-2 bg-surface-3 px-2 py-0.5 rounded font-mono">MLflow: {result.mlflow_run_id.slice(0, 8)}</span>}
                </p>
                <div className="prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown>{result.hypothesis.hypothesis_text}</ReactMarkdown>
                </div>
              </div>

              {result.evidence_summary && (
                <div className="bg-surface-2 border border-surface-3 rounded-xl p-6">
                  <h2 className="text-lg font-semibold text-white mb-3">Evidence Summary</h2>
                  <p className="text-slate-300 text-sm leading-relaxed">{result.evidence_summary}</p>
                </div>
              )}

              {result.critique && (
                <div className="bg-surface-2 border border-surface-3 rounded-xl p-6">
                  <h2 className="text-lg font-semibold text-white mb-4">Critique</h2>
                  <DebateCard entry={result.critique} label="Critic Review" />
                </div>
              )}

              {result.contradictions.length > 0 && (
                <div className="bg-surface-2 border border-surface-3 rounded-xl p-6">
                  <h2 className="text-lg font-semibold text-white mb-4">
                    Contradictions Detected <span className="text-sm font-normal text-slate-400">({result.contradictions.length})</span>
                  </h2>
                  <div className="space-y-3">
                    {result.contradictions.map((c, i) => <ContradictionCard key={i} item={c} index={i} />)}
                  </div>
                </div>
              )}

              {result.tool_results && result.tool_results.length > 0 && (
                <div className="bg-surface-2 border border-surface-3 rounded-xl p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <h2 className="text-lg font-semibold text-white">Tools Used</h2>
                    <span className="text-sm text-slate-400">({result.tool_results.length})</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-primary-900 text-primary-300 border border-primary-700">
                      auto-selected
                    </span>
                  </div>
                  <div className="space-y-2">
                    {result.tool_results.map((tr, i) => <ToolResultCard key={i} result={tr} />)}
                  </div>
                </div>
              )}

              {result.debate.length > 0 && (
                <div className="bg-surface-2 border border-surface-3 rounded-xl p-6">
                  <h2 className="text-lg font-semibold text-white mb-4">Debate</h2>
                  <div className="space-y-3">
                    {result.debate.map((d, i) => (
                      <DebateCard
                        key={i}
                        entry={d}
                        label={d.role === "pro" ? "For the hypothesis" : "Against the hypothesis"}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </AuthGuard>
  );
}
