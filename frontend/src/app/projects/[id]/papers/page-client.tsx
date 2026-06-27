"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { useDropzone } from "react-dropzone";
import AuthGuard from "@/components/layout/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import api from "@/lib/api";
import type { Paper } from "@/types";
import Link from "next/link";
import clsx from "clsx";

const statusColor: Record<string, string> = {
  pending: "bg-yellow-900 text-yellow-300",
  done: "bg-green-900 text-green-300",
  failed: "bg-red-900 text-red-300",
};

export default function PapersPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [uploading, setUploading] = useState(false);
  const [meta, setMeta] = useState({ title: "", authors: "", year: "" });

  async function load() {
    const r = await api.get(`/projects/${projectId}/papers`);
    setPapers(r.data);
  }

  useEffect(() => { load(); }, [projectId]);

  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0];
    if (!file || !meta.title) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("metadata", JSON.stringify({
      title: meta.title,
      authors: meta.authors.split(",").map((a) => a.trim()).filter(Boolean),
      year: meta.year ? parseInt(meta.year) : null,
    }));
    try {
      await api.post(`/projects/${projectId}/papers`, formData);
      setMeta({ title: "", authors: "", year: "" });
      load();
    } finally {
      setUploading(false);
    }
  }, [meta, projectId]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept: { "application/pdf": [".pdf"] } });

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8">
          <div className="flex items-center gap-3 mb-6">
            <Link href={`/projects/${projectId}`} className="text-slate-400 hover:text-slate-300 text-sm">← Project</Link>
            <h1 className="text-2xl font-bold text-white">Papers</h1>
          </div>

          <div className="bg-surface-2 border border-surface-3 rounded-xl p-6 mb-8">
            <h2 className="text-lg font-semibold text-white mb-4">Upload Paper</h2>
            <div className="grid grid-cols-3 gap-3 mb-4">
              <input placeholder="Title *" value={meta.title} onChange={(e) => setMeta({ ...meta, title: e.target.value })} className="col-span-3 bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500" />
              <input placeholder="Authors (comma separated)" value={meta.authors} onChange={(e) => setMeta({ ...meta, authors: e.target.value })} className="col-span-2 bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500" />
              <input placeholder="Year" value={meta.year} onChange={(e) => setMeta({ ...meta, year: e.target.value })} className="bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500" />
            </div>
            <div
              {...getRootProps()}
              className={clsx("border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors", isDragActive ? "border-primary-500 bg-primary-900/20" : "border-slate-600 hover:border-slate-500")}
            >
              <input {...getInputProps()} />
              <p className="text-slate-400">{isDragActive ? "Drop PDF here…" : "Drag & drop a PDF, or click to select"}</p>
              {uploading && <p className="text-primary-400 text-sm mt-2">Uploading…</p>}
            </div>
          </div>

          <div className="space-y-3">
            {papers.map((p) => (
              <div key={p.id} className="bg-surface-2 border border-surface-3 rounded-xl p-5 flex items-start justify-between">
                <div>
                  <p className="font-semibold text-white">{p.title}</p>
                  {p.authors.length > 0 && <p className="text-slate-400 text-sm mt-0.5">{p.authors.join(", ")}</p>}
                  {p.abstract && <p className="text-slate-500 text-xs mt-1 line-clamp-2">{p.abstract}</p>}
                </div>
                <div className="flex flex-col items-end gap-2 ml-4 shrink-0">
                  <span className={clsx("text-xs px-2 py-0.5 rounded font-medium", statusColor[p.embedding_status] || "bg-surface-3 text-slate-300")}>
                    {p.embedding_status}
                  </span>
                  {p.embedding_status === "done" && (
                    <span className="text-xs text-slate-500">{p.chunk_count} chunks</span>
                  )}
                </div>
              </div>
            ))}
            {papers.length === 0 && <p className="text-slate-500 text-center py-12">No papers uploaded yet.</p>}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
