"use client";
import { useEffect, useState } from "react";
import AuthGuard from "@/components/layout/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import api from "@/lib/api";
import type { Project } from "@/types";
import Link from "next/link";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", tags: "" });

  async function load() {
    const r = await api.get("/projects");
    setProjects(r.data);
  }

  useEffect(() => { load(); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    await api.post("/projects", {
      name: form.name,
      description: form.description || null,
      tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
    });
    setCreating(false);
    setForm({ name: "", description: "", tags: "" });
    load();
  }

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-white">Projects</h1>
            <button
              onClick={() => setCreating(!creating)}
              className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              {creating ? "Cancel" : "New Project"}
            </button>
          </div>

          {creating && (
            <form onSubmit={handleCreate} className="bg-surface-2 border border-surface-3 rounded-xl p-6 mb-6 space-y-4">
              <h2 className="text-lg font-semibold text-white">New Project</h2>
              <input
                placeholder="Project name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
                className="w-full bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <textarea
                placeholder="Description (optional)"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={2}
                className="w-full bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
              />
              <input
                placeholder="Tags (comma separated)"
                value={form.tags}
                onChange={(e) => setForm({ ...form, tags: e.target.value })}
                className="w-full bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <button
                type="submit"
                className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                Create
              </button>
            </form>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {projects.map((p) => (
              <Link
                key={p.id}
                href={`/projects/${p.id}`}
                className="block bg-surface-2 border border-surface-3 rounded-xl p-5 hover:border-primary-500 transition-colors"
              >
                <h3 className="font-semibold text-white mb-1">{p.name}</h3>
                {p.description && <p className="text-slate-400 text-sm mb-3 line-clamp-2">{p.description}</p>}
                <div className="flex flex-wrap gap-1">
                  {p.tags.map((t) => (
                    <span key={t} className="text-xs bg-surface-3 text-slate-300 px-2 py-0.5 rounded">{t}</span>
                  ))}
                </div>
                <p className="text-xs text-slate-500 mt-3">{new Date(p.created_at).toLocaleDateString()}</p>
              </Link>
            ))}
            {projects.length === 0 && (
              <p className="text-slate-500 col-span-3 text-center py-12">No projects yet. Create your first one.</p>
            )}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
