"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import AuthGuard from "@/components/layout/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import api from "@/lib/api";
import type { Experiment, EvaluationOut, Hypothesis, HypothesisReviewStatus } from "@/types";
import Link from "next/link";
import clsx from "clsx";

const statusColor: Record<string, string> = {
  draft: "bg-slate-700 text-slate-300",
  running: "bg-yellow-900 text-yellow-300",
  completed: "bg-green-900 text-green-300",
  failed: "bg-red-900 text-red-300",
};

const reviewStyle: Record<HypothesisReviewStatus, { chip: string; label: string }> = {
  candidate:    { chip: "bg-amber-900 text-amber-300 border border-amber-700",   label: "Candidate" },
  under_review: { chip: "bg-blue-900 text-blue-300 border border-blue-700",      label: "Under Review" },
  accepted:     { chip: "bg-green-900 text-green-300 border border-green-700",   label: "Accepted" },
  rejected:     { chip: "bg-red-900 text-red-300 border border-red-700",         label: "Rejected" },
};

const verdictStyle: Record<string, { bg: string; text: string; label: string }> = {
  strong:   { bg: "bg-green-900",  text: "text-green-300",  label: "Strong" },
  moderate: { bg: "bg-yellow-900", text: "text-yellow-300", label: "Moderate" },
  weak:     { bg: "bg-red-900",    text: "text-red-300",    label: "Weak" },
};

function ReviewStatusBadge({ status }: { status: HypothesisReviewStatus }) {
  const s = reviewStyle[status];
  return <span className={clsx("text-xs px-2 py-0.5 rounded-full shrink-0", s.chip)}>{s.label}</span>;
}

function QualityBadge({ eval: ev, onEvaluate }: { eval: EvaluationOut | undefined; onEvaluate: () => void }) {
  if (!ev) {
    return (
      <button
        onClick={(e) => { e.stopPropagation(); onEvaluate(); }}
        className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-400 hover:bg-slate-600 transition-colors shrink-0"
      >
        Evaluate
      </button>
    );
  }
  const style = verdictStyle[ev.verdict] ?? verdictStyle.weak;
  return (
    <span title={`Overall: ${(ev.overall_score * 100).toFixed(0)}%`}
      className={clsx("text-xs px-2 py-0.5 rounded shrink-0", style.bg, style.text)}>
      {style.label} · {(ev.overall_score * 100).toFixed(0)}%
    </span>
  );
}

function ReviewActions({ hypothesis, projectId, onUpdated }: {
  hypothesis: Hypothesis;
  projectId: string;
  onUpdated: (h: Hypothesis) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [showNotes, setShowNotes] = useState(false);
  const [notes, setNotes] = useState("");

  if (hypothesis.review_status === "accepted" || hypothesis.review_status === "rejected") {
    return (
      <div className="text-xs text-slate-500 mt-1">
        {hypothesis.review_notes && <span>Notes: {hypothesis.review_notes}</span>}
      </div>
    );
  }

  async function decide(decision: "accepted" | "rejected") {
    setBusy(true);
    try {
      const r = await api.post(`/projects/${projectId}/hypotheses/${hypothesis.id}/review`, {
        decision,
        notes: notes || null,
      });
      onUpdated(r.data);
      setShowNotes(false);
      setNotes("");
    } catch {
      // ignore
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-2 border-t border-slate-700 pt-2 space-y-2">
      <p className="text-xs text-amber-400 font-medium">
        This hypothesis is a candidate — requires your review before use.
      </p>
      {showNotes ? (
        <div className="space-y-2">
          <textarea
            placeholder="Optional review notes…"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="w-full text-xs bg-surface-2 border border-slate-600 rounded px-2 py-1 text-white resize-none focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
          <div className="flex gap-2">
            <button
              onClick={() => decide("accepted")}
              disabled={busy}
              className="text-xs px-3 py-1.5 rounded bg-green-700 hover:bg-green-600 text-white transition-colors disabled:opacity-50"
            >
              Accept
            </button>
            <button
              onClick={() => decide("rejected")}
              disabled={busy}
              className="text-xs px-3 py-1.5 rounded bg-red-800 hover:bg-red-700 text-white transition-colors disabled:opacity-50"
            >
              Reject
            </button>
            <button
              onClick={() => setShowNotes(false)}
              className="text-xs px-3 py-1.5 rounded bg-slate-700 hover:bg-slate-600 text-slate-300 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowNotes(true)}
          className="text-xs px-3 py-1.5 rounded bg-slate-700 hover:bg-slate-600 text-slate-300 transition-colors"
        >
          Review this hypothesis
        </button>
      )}
    </div>
  );
}

export default function ExperimentsPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<Experiment | null>(null);
  const [form, setForm] = useState({ title: "", description: "" });
  const [evaluations, setEvaluations] = useState<Record<string, EvaluationOut>>({});
  const [evaluating, setEvaluating] = useState<string | null>(null);

  async function load() {
    const r = await api.get(`/projects/${projectId}/experiments`);
    setExperiments(r.data);
  }

  async function loadEvaluations() {
    try {
      const r = await api.get(`/projects/${projectId}/evaluations`);
      const map: Record<string, EvaluationOut> = {};
      for (const ev of r.data as EvaluationOut[]) map[ev.hypothesis_id] = ev;
      setEvaluations(map);
    } catch { /* evaluations not yet available */ }
  }

  useEffect(() => { load(); loadEvaluations(); }, [projectId]);

  async function loadDetail(exp: Experiment) {
    const r = await api.get(`/projects/${projectId}/experiments/${exp.id}`);
    setSelected(r.data);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    await api.post(`/projects/${projectId}/experiments`, form);
    setCreating(false);
    setForm({ title: "", description: "" });
    load();
  }

  async function handleEvaluate(hypothesisId: string) {
    setEvaluating(hypothesisId);
    try {
      const r = await api.post(`/projects/${projectId}/hypotheses/${hypothesisId}/evaluate`, {});
      setEvaluations((prev) => ({ ...prev, [hypothesisId]: r.data }));
    } catch { /* ignore */ } finally { setEvaluating(null); }
  }

  function updateHypothesisInSelected(updated: Hypothesis) {
    setSelected((prev) => {
      if (!prev?.hypotheses) return prev;
      return {
        ...prev,
        hypotheses: prev.hypotheses.map((h) => h.id === updated.id ? updated : h),
      };
    });
  }

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Link href={`/projects/${projectId}`} className="text-slate-400 hover:text-slate-300 text-sm">← Project</Link>
              <h1 className="text-2xl font-bold text-white">Experiments</h1>
            </div>
            <button onClick={() => setCreating(!creating)} className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
              {creating ? "Cancel" : "New Experiment"}
            </button>
          </div>

          {creating && (
            <form onSubmit={handleCreate} className="bg-surface-2 border border-surface-3 rounded-xl p-6 mb-6 space-y-4">
              <input placeholder="Experiment title" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="w-full bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500" />
              <textarea placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} className="w-full bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none" />
              <button type="submit" className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Create</button>
            </form>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-3">
              {experiments.map((exp) => (
                <button key={exp.id} onClick={() => loadDetail(exp)} className="w-full text-left bg-surface-2 border border-surface-3 hover:border-primary-500 rounded-xl p-5 transition-colors">
                  <div className="flex items-start justify-between">
                    <p className="font-semibold text-white">{exp.title}</p>
                    <span className={clsx("text-xs px-2 py-0.5 rounded ml-2 shrink-0", statusColor[exp.status])}>{exp.status}</span>
                  </div>
                  {exp.description && <p className="text-slate-400 text-sm mt-1">{exp.description}</p>}
                  <p className="text-xs text-slate-500 mt-2">{new Date(exp.created_at).toLocaleDateString()}</p>
                </button>
              ))}
              {experiments.length === 0 && <p className="text-slate-500 text-center py-12">No experiments yet.</p>}
            </div>

            {selected && (
              <div className="bg-surface-2 border border-surface-3 rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-1">{selected.title}</h3>
                <span className={clsx("text-xs px-2 py-0.5 rounded", statusColor[selected.status])}>{selected.status}</span>

                <h4 className="text-sm font-medium text-slate-300 mt-4 mb-2">
                  Hypothesis Candidates ({selected.hypotheses?.length ?? 0})
                </h4>
                <div className="space-y-4 max-h-[32rem] overflow-y-auto">
                  {selected.hypotheses?.map((h) => (
                    <div key={h.id} className="bg-surface-3 rounded-lg p-3">
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <p className="text-xs text-slate-400">{h.question}</p>
                        <ReviewStatusBadge status={h.review_status ?? "candidate"} />
                      </div>
                      <p className="text-sm text-white leading-snug">{h.hypothesis_text}</p>

                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        <span className="text-xs text-slate-500">{h.agent_used}</span>
                        {h.confidence_score !== null && (
                          <span className="text-xs text-slate-500">{(h.confidence_score * 100).toFixed(0)}% confidence</span>
                        )}
                        {evaluating === h.id ? (
                          <span className="text-xs text-slate-400">Evaluating…</span>
                        ) : (
                          <QualityBadge eval={evaluations[h.id]} onEvaluate={() => handleEvaluate(h.id)} />
                        )}
                      </div>

                      {evaluations[h.id] && (
                        <div className="mt-2 space-y-1">
                          {evaluations[h.id].dimension_scores.map((d) => (
                            <div key={d.name} className="flex items-center gap-2">
                              <span className="text-xs text-slate-500 w-32 truncate">{d.name.replace(/_/g, " ")}</span>
                              <div className="flex-1 bg-slate-700 rounded-full h-1">
                                <div className="bg-primary-500 h-1 rounded-full" style={{ width: `${(d.score * 100).toFixed(0)}%` }} />
                              </div>
                              <span className="text-xs text-slate-400 w-8 text-right">{(d.score * 100).toFixed(0)}%</span>
                            </div>
                          ))}
                        </div>
                      )}

                      <ReviewActions
                        hypothesis={h}
                        projectId={projectId}
                        onUpdated={updateHypothesisInSelected}
                      />
                    </div>
                  ))}
                  {(selected.hypotheses?.length ?? 0) === 0 && (
                    <p className="text-slate-500 text-xs">No hypotheses yet. Run a research workflow.</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
