"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import AuthGuard from "@/components/layout/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import api from "@/lib/api";
import Link from "next/link";

interface Summary {
  project: { id: string; name: string; description: string | null; tags: string[] };
  paper_count: number;
  experiment_count: number;
  note_count: number;
}

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const [summary, setSummary] = useState<Summary | null>(null);

  useEffect(() => {
    if (id) api.get(`/projects/${id}/summary`).then((r) => setSummary(r.data)).catch(() => {});
  }, [id]);

  if (!summary) return (
    <AuthGuard>
      <div className="flex min-h-screen"><Sidebar /><main className="flex-1 p-8"><p className="text-slate-400">Loading…</p></main></div>
    </AuthGuard>
  );

  const tabs = [
    { href: `/projects/${id}/papers`, label: "Papers", count: summary.paper_count },
    { href: `/projects/${id}/experiments`, label: "Experiments", count: summary.experiment_count },
    { href: `/projects/${id}/notes`, label: "Notes", count: summary.note_count },
    { href: `/projects/${id}/report`, label: "Report", count: null },
    { href: `/projects/${id}/tracking`, label: "Tracking", count: null },
    { href: `/projects/${id}/graph`, label: "Graph", count: null },
    { href: `/projects/${id}/simulations`, label: "Simulations", count: null },
  ];

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8">
          <div className="mb-6">
            <Link href="/projects" className="text-slate-400 hover:text-slate-300 text-sm">← Projects</Link>
            <h1 className="text-2xl font-bold text-white mt-2">{summary.project.name}</h1>
            {summary.project.description && (
              <p className="text-slate-400 mt-1">{summary.project.description}</p>
            )}
            <div className="flex gap-2 mt-2">
              {summary.project.tags.map((t) => (
                <span key={t} className="text-xs bg-surface-3 text-slate-300 px-2 py-0.5 rounded">{t}</span>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-8">
            {tabs.map((tab) => (
              <Link
                key={tab.href}
                href={tab.href}
                className="bg-surface-2 border border-surface-3 hover:border-primary-500 rounded-xl p-5 transition-colors"
              >
                {tab.count !== null
                  ? <p className="text-3xl font-bold text-white">{tab.count}</p>
                  : <p className="text-3xl font-bold text-primary-400">→</p>}
                <p className="text-slate-400 text-sm mt-1">{tab.label}</p>
              </Link>
            ))}
          </div>

          <div className="flex gap-3">
            {tabs.map((tab) => (
              <Link
                key={tab.href}
                href={tab.href}
                className="bg-primary-700 hover:bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                View {tab.label}
              </Link>
            ))}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
