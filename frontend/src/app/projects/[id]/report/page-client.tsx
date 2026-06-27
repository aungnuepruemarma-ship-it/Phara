"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import AuthGuard from "@/components/layout/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import api from "@/lib/api";
import type { ProjectReport } from "@/types";
import Link from "next/link";
import ReactMarkdown from "react-markdown";

export default function ReportPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [report, setReport] = useState<ProjectReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function generate() {
    setLoading(true);
    setError("");
    try {
      const r = await api.get(`/projects/${projectId}/report`);
      setReport(r.data);
    } catch {
      setError("Failed to generate report.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { generate(); }, [projectId]);

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8 max-w-4xl">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Link href={`/projects/${projectId}`} className="text-slate-400 hover:text-slate-300 text-sm">← Project</Link>
              <h1 className="text-2xl font-bold text-white">Research Report</h1>
            </div>
            <button onClick={generate} disabled={loading} className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 transition-colors">
              {loading ? "Generating…" : "Regenerate"}
            </button>
          </div>

          {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
          {loading && <p className="text-slate-400">Generating synthesis…</p>}

          {report && (
            <div className="space-y-6">
              {/* Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-surface-2 border border-surface-3 rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-white">{report.experiment_count}</p>
                  <p className="text-xs text-slate-400 mt-1">Experiments</p>
                </div>
                <div className="bg-surface-2 border border-surface-3 rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-white">{report.hypothesis_count}</p>
                  <p className="text-xs text-slate-400 mt-1">Hypotheses</p>
                </div>
                <div className="bg-surface-2 border border-surface-3 rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-white">
                    {report.avg_confidence !== null ? `${(report.avg_confidence * 100).toFixed(0)}%` : "—"}
                  </p>
                  <p className="text-xs text-slate-400 mt-1">Avg Confidence</p>
                </div>
                <div className="bg-surface-2 border border-surface-3 rounded-xl p-4 text-center">
                  <p className="text-sm font-semibold text-white truncate">{report.top_agents[0] ?? "—"}</p>
                  <p className="text-xs text-slate-400 mt-1">Top Agent</p>
                </div>
              </div>

              {/* Synthesis */}
              <div className="bg-surface-2 border border-primary-700 rounded-xl p-6">
                <h2 className="text-lg font-semibold text-white mb-4">Research Synthesis</h2>
                <div className="prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown>{report.synthesis}</ReactMarkdown>
                </div>
                <p className="text-xs text-slate-500 mt-4">
                  Generated {new Date(report.generated_at).toLocaleString()}
                </p>
              </div>

              {/* Hypothesis log */}
              <div className="bg-surface-2 border border-surface-3 rounded-xl p-6">
                <h2 className="text-lg font-semibold text-white mb-4">Hypothesis Log ({report.hypotheses.length})</h2>
                <div className="space-y-3 max-h-[600px] overflow-y-auto">
                  {report.hypotheses.map((h, i) => (
                    <div key={h.id} className="bg-surface-3 rounded-lg p-4">
                      <div className="flex items-start justify-between mb-1">
                        <p className="text-xs text-slate-400 font-mono">#{i + 1} · {h.agent_used}</p>
                        {h.confidence_score !== null && (
                          <span className="text-xs text-slate-400">{(h.confidence_score * 100).toFixed(0)}%</span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 italic mb-2">{h.question}</p>
                      <p className="text-sm text-white">{h.hypothesis_text}</p>
                    </div>
                  ))}
                  {report.hypotheses.length === 0 && (
                    <p className="text-slate-500 text-sm text-center py-8">No hypotheses yet. Run a research workflow to generate some.</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </AuthGuard>
  );
}
