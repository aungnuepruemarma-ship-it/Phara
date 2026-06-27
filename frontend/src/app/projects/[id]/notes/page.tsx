"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import AuthGuard from "@/components/layout/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import api from "@/lib/api";
import type { Note } from "@/types";
import ReactMarkdown from "react-markdown";
import Link from "next/link";

export default function NotesPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [notes, setNotes] = useState<Note[]>([]);
  const [selected, setSelected] = useState<Note | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ title: "", content: "" });

  async function load() {
    const r = await api.get(`/projects/${projectId}/notes`);
    setNotes(r.data);
  }

  useEffect(() => { load(); }, [projectId]);

  async function handleSave() {
    if (selected) {
      await api.put(`/projects/${projectId}/notes/${selected.id}`, form);
    } else {
      await api.post(`/projects/${projectId}/notes`, form);
    }
    setEditing(false);
    setSelected(null);
    setForm({ title: "", content: "" });
    load();
  }

  function openNote(note: Note) {
    setSelected(note);
    setForm({ title: note.title, content: note.content });
    setEditing(false);
  }

  function newNote() {
    setSelected(null);
    setForm({ title: "", content: "" });
    setEditing(true);
  }

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Link href={`/projects/${projectId}`} className="text-slate-400 hover:text-slate-300 text-sm">← Project</Link>
              <h1 className="text-2xl font-bold text-white">Notes</h1>
            </div>
            <button onClick={newNote} className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
              New Note
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="space-y-2">
              {notes.map((n) => (
                <button key={n.id} onClick={() => openNote(n)} className="w-full text-left bg-surface-2 border border-surface-3 hover:border-primary-500 rounded-lg p-4 transition-colors">
                  <p className="font-medium text-white text-sm">{n.title}</p>
                  <p className="text-xs text-slate-500 mt-1">{new Date(n.updated_at).toLocaleDateString()}</p>
                </button>
              ))}
              {notes.length === 0 && <p className="text-slate-500 text-sm text-center py-8">No notes yet.</p>}
            </div>

            <div className="lg:col-span-2 bg-surface-2 border border-surface-3 rounded-xl p-6">
              {editing ? (
                <div className="space-y-4 h-full">
                  <input
                    placeholder="Note title"
                    value={form.title}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                    className="w-full bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                  <textarea
                    placeholder="Write in Markdown…"
                    value={form.content}
                    onChange={(e) => setForm({ ...form, content: e.target.value })}
                    rows={16}
                    className="w-full bg-surface-3 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none font-mono text-sm"
                  />
                  <div className="flex gap-3">
                    <button onClick={handleSave} className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Save</button>
                    <button onClick={() => setEditing(false)} className="text-slate-400 hover:text-slate-300 text-sm">Cancel</button>
                  </div>
                </div>
              ) : selected ? (
                <div>
                  <div className="flex items-start justify-between mb-4">
                    <h2 className="text-xl font-semibold text-white">{selected.title}</h2>
                    <button onClick={() => setEditing(true)} className="text-primary-400 hover:text-primary-300 text-sm">Edit</button>
                  </div>
                  <div className="prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown>{selected.content}</ReactMarkdown>
                  </div>
                </div>
              ) : (
                <p className="text-slate-500 text-center py-16">Select a note or create a new one.</p>
              )}
            </div>
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
