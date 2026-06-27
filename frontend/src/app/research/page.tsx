"use client";
import { useEffect, useState } from "react";
import AuthGuard from "@/components/layout/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import api from "@/lib/api";
import type { Project, Experiment, WorkflowResult } from "@/types";
import ReactMarkdown from "react-markdown";

export default function ResearchPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [agents, setAgents] = useState<{ name: string; description: string }[]>([]);
  const [form, setForm] = useState({ question: "", project_id: "", experiment_id: "", agent_name: "math_research_agent" });
  const [result, setResult] = useState<WorkflowResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/projects").then((r) => setProjects(r.data));
    api.get("/research/agents").then((r) => setAgents(r.data));
  }, []);

  useEffect(() => {
    if (form.project_id) {
      api.get(`/projects/${form.project_id}/experiments`).then((r) => setExperiments(r.data));
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
                <select value={form.experiment_id} onChange={(e) => setForm({ ...form, experiment_id: e.target.value })} required className="w-full bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500">
                  <option value="">Select…</option>
                  {experiments.map((exp) => <option key={exp.id} value={exp.id}>{exp.title}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Agent</label>
                <select value={form.agent_name} onChange={(e) => setForm({ ...form, agent_name: e.target.value })} className="w-full bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500">
                  {agents.map((a) => <option key={a.name} value={a.name}>{a.name}</option>)}
                </select>
              </div>
            </div>

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
            </div>
          )}
        </main>
      </div>
    </AuthGuard>
  );
}
