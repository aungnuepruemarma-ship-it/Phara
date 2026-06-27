"use client";
import { useEffect, useState } from "react";
import AuthGuard from "@/components/layout/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import api from "@/lib/api";
import type { Project, Hypothesis, Experiment } from "@/types";
import Link from "next/link";

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-surface-2 border border-surface-3 rounded-xl p-5">
      <p className="text-slate-400 text-sm">{label}</p>
      <p className="text-3xl font-bold text-white mt-1">{value}</p>
    </div>
  );
}

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);

  useEffect(() => {
    api.get("/projects").then((r) => setProjects(r.data)).catch(() => {});
    api.get("/research/history").then((r) => setHypotheses(r.data)).catch(() => {});
  }, []);

  const totalExperiments = projects.length;

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8">
          <h1 className="text-2xl font-bold text-white mb-6">Dashboard</h1>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
            <StatCard label="Projects" value={projects.length} />
            <StatCard label="Hypotheses Generated" value={hypotheses.length} />
            <StatCard label="Recent Activity" value={Math.min(5, hypotheses.length)} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <section>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white">Recent Projects</h2>
                <Link href="/projects" className="text-primary-400 hover:text-primary-300 text-sm">
                  View all
                </Link>
              </div>
              <div className="space-y-3">
                {projects.slice(0, 5).map((p) => (
                  <Link
                    key={p.id}
                    href={`/projects/${p.id}`}
                    className="block bg-surface-2 border border-surface-3 rounded-lg p-4 hover:border-primary-500 transition-colors"
                  >
                    <p className="font-medium text-white">{p.name}</p>
                    {p.description && <p className="text-slate-400 text-sm mt-1 truncate">{p.description}</p>}
                    <div className="flex gap-2 mt-2">
                      {p.tags.map((t) => (
                        <span key={t} className="text-xs bg-surface-3 text-slate-300 px-2 py-0.5 rounded">
                          {t}
                        </span>
                      ))}
                    </div>
                  </Link>
                ))}
                {projects.length === 0 && (
                  <p className="text-slate-500 text-sm">No projects yet. <Link href="/projects" className="text-primary-400">Create one.</Link></p>
                )}
              </div>
            </section>

            <section>
              <h2 className="text-lg font-semibold text-white mb-4">Recent Hypotheses</h2>
              <div className="space-y-3">
                {hypotheses.slice(0, 5).map((h) => (
                  <div key={h.id} className="bg-surface-2 border border-surface-3 rounded-lg p-4">
                    <p className="text-sm text-slate-300 font-medium mb-1 line-clamp-2">{h.question}</p>
                    <p className="text-xs text-slate-400 line-clamp-3">{h.hypothesis_text}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-xs bg-primary-900 text-primary-300 px-2 py-0.5 rounded">
                        {h.agent_used}
                      </span>
                      {h.confidence_score !== null && (
                        <span className="text-xs text-slate-500">
                          {(h.confidence_score * 100).toFixed(0)}% confidence
                        </span>
                      )}
                    </div>
                  </div>
                ))}
                {hypotheses.length === 0 && (
                  <p className="text-slate-500 text-sm">No hypotheses yet. Run a <Link href="/research" className="text-primary-400">research workflow.</Link></p>
                )}
              </div>
            </section>
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
