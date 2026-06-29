"use client";
import { useEffect, useRef, useState } from "react";
import AuthGuard from "@/components/layout/AuthGuard";
import Sidebar from "@/components/layout/Sidebar";
import api from "@/lib/api";
import { extractErrorMessage } from "@/lib/errors";
import type { Project, RoundtableResult, AgentTurn } from "@/types";
import ReactMarkdown from "react-markdown";

interface AgentInfo {
  name: string;
  description: string;
}

// Tools/skills the panel can use. code_sandbox runs Python experiments.
const TOOL_OPTIONS: { name: string; label: string }[] = [
  { name: "web_search", label: "Real-time web" },
  { name: "wikipedia_search", label: "Wikipedia" },
  { name: "arxiv_search", label: "arXiv" },
  { name: "semantic_scholar_search", label: "Semantic Scholar" },
  { name: "code_sandbox", label: "🧪 Code sandbox" },
];

type ChatMessage =
  | { kind: "user"; text: string }
  | { kind: "assistant"; result: RoundtableResult };

// Stable color per agent for visual grouping.
const AGENT_COLORS: Record<string, string> = {
  math_research_agent: "text-sky-300 border-sky-700",
  ai_research_agent: "text-violet-300 border-violet-700",
  cs_research_agent: "text-emerald-300 border-emerald-700",
  physics_research_agent: "text-amber-300 border-amber-700",
  biology_research_agent: "text-rose-300 border-rose-700",
  critic_agent: "text-red-300 border-red-700",
  planner_agent: "text-teal-300 border-teal-700",
};
const agentColor = (n: string) => AGENT_COLORS[n] || "text-slate-300 border-slate-600";
const shortName = (n: string) => n.replace(/_/g, " ").replace(/ agent$/, "");

function AgentBubble({ turn }: { turn: AgentTurn }) {
  return (
    <div className={`border-l-2 pl-3 ${agentColor(turn.agent_name)}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-xs font-semibold ${agentColor(turn.agent_name).split(" ")[0]}`}>
          {shortName(turn.agent_name)}
        </span>
        <span className="text-[10px] uppercase tracking-wide text-slate-500">{turn.role}</span>
        <span className="text-[10px] text-slate-500">{(turn.confidence * 100).toFixed(0)}%</span>
      </div>
      <div className="prose prose-invert prose-sm max-w-none text-slate-300">
        <ReactMarkdown>{turn.content}</ReactMarkdown>
      </div>
    </div>
  );
}

function LiveDataCard({ result }: { result: RoundtableResult }) {
  const ok = result.tool_results.filter((t) => t.success);
  if (ok.length === 0) return null;
  return (
    <div className="bg-surface-3/50 border border-surface-3 rounded-lg p-4">
      <p className="text-xs font-semibold text-cyan-300 uppercase tracking-wide mb-2">
        Live data fetched
      </p>
      <ul className="space-y-1">
        {ok.map((t, i) => (
          <li key={i} className="text-xs text-slate-400">
            <span className="font-medium text-slate-200">{t.tool_name}</span>
            {" — "}
            {Array.isArray(t.output) ? `${t.output.length} result(s)` : "fetched"}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ExperimentCard({ turn }: { turn: AgentTurn }) {
  return (
    <div className="bg-black/30 border border-emerald-800 rounded-lg p-4">
      <p className="text-xs font-semibold text-emerald-300 uppercase tracking-wide mb-2">
        🧪 Code sandbox experiment
      </p>
      <div className="prose prose-invert prose-sm max-w-none">
        <ReactMarkdown>{turn.content}</ReactMarkdown>
      </div>
    </div>
  );
}

function AssistantTurnView({ result }: { result: RoundtableResult }) {
  const perspectives = result.turns.filter((t) => t.role === "perspective");
  const rebuttals = result.turns.filter((t) => t.role === "rebuttal");
  const experiment = result.turns.find((t) => t.role === "experiment");
  return (
    <div className="space-y-5">
      <LiveDataCard result={result} />

      {perspectives.length > 0 && (
        <div className="space-y-4">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Round 1 · Perspectives</p>
          {perspectives.map((t, i) => <AgentBubble key={`p${i}`} turn={t} />)}
        </div>
      )}

      {experiment && <ExperimentCard turn={experiment} />}

      {result.patterns.length > 0 && (
        <div className="bg-surface-3/50 border border-surface-3 rounded-lg p-4">
          <p className="text-xs font-semibold text-primary-300 uppercase tracking-wide mb-2">
            Cross-domain patterns detected
          </p>
          <ul className="space-y-1.5">
            {result.patterns.map((p, i) => (
              <li key={i} className="text-sm text-slate-300">
                <span className="font-medium text-white">{p.pattern_type}</span>
                {p.domains_seen.length > 0 && (
                  <span className="text-xs text-slate-500"> · {p.domains_seen.join(", ")}</span>
                )}
                <span className="text-slate-400"> — {p.description}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {rebuttals.length > 0 && (
        <div className="space-y-4">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Round 2 · Cross-talk</p>
          {rebuttals.map((t, i) => <AgentBubble key={`r${i}`} turn={t} />)}
        </div>
      )}

      <div className="bg-surface-2 border border-primary-700 rounded-xl p-5">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-primary-300 uppercase tracking-wide">Final synthesis</h3>
          <span className="text-xs text-slate-400">{(result.final_confidence * 100).toFixed(0)}% confidence</span>
        </div>
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown>{result.final_text}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [projectId, setProjectId] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [tools, setTools] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.get("/projects").then((r) => {
      setProjects(r.data);
      if (r.data.length && !projectId) setProjectId(r.data[0].id);
    }).catch(() => {});
    api.get("/research/agents").then((r) => {
      setAgents(r.data);
      // Default selection: the five domain generators.
      setSelected(
        r.data
          .map((a: AgentInfo) => a.name)
          .filter((n: string) => !["critic_agent", "planner_agent"].includes(n))
          .slice(0, 3)
      );
    }).catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, running]);

  function toggleAgent(name: string) {
    setSelected((s) => (s.includes(name) ? s.filter((n) => n !== name) : [...s, name]));
  }

  function toggleTool(name: string) {
    setTools((s) => (s.includes(name) ? s.filter((n) => n !== name) : [...s, name]));
  }

  async function send() {
    const question = input.trim();
    if (!question || running) return;
    if (!projectId) { setError("Select a project first."); return; }
    if (selected.length === 0) { setError("Select at least one agent."); return; }
    setError("");

    const history = messages.map((m) =>
      m.kind === "user"
        ? { role: "user", content: m.text }
        : { role: "assistant", content: m.result.final_text }
    );

    setMessages((prev) => [...prev, { kind: "user", text: question }]);
    setInput("");
    setRunning(true);
    try {
      const r = await api.post("/research/roundtable", {
        question,
        project_id: projectId,
        agent_names: selected,
        tools,
        history,
      });
      setMessages((prev) => [...prev, { kind: "assistant", result: r.data as RoundtableResult }]);
    } catch (err) {
      setError(extractErrorMessage(err, "The panel failed to respond. Try again."));
    } finally {
      setRunning(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 flex flex-col h-screen">
          {/* Controls */}
          <div className="border-b border-surface-3 px-6 py-3 bg-surface-2/50">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-base font-semibold text-white mr-2">Agent Chat</h1>
              <select
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                className="bg-surface-3 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">Select project…</option>
                {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div className="flex flex-wrap gap-2 mt-3">
              {agents.map((a) => {
                const on = selected.includes(a.name);
                return (
                  <button
                    key={a.name}
                    type="button"
                    title={a.description}
                    onClick={() => toggleAgent(a.name)}
                    className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                      on
                        ? `bg-surface-3 ${agentColor(a.name)}`
                        : "border-slate-700 text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    {on ? "✓ " : ""}{shortName(a.name)}
                  </button>
                );
              })}
              <span className="text-xs text-slate-500 self-center ml-1">
                {selected.length} selected · up to 4 used
              </span>
            </div>
            <div className="flex flex-wrap gap-2 mt-2 items-center">
              <span className="text-xs text-slate-500 mr-1">Tools:</span>
              {TOOL_OPTIONS.map((t) => {
                const on = tools.includes(t.name);
                return (
                  <button
                    key={t.name}
                    type="button"
                    onClick={() => toggleTool(t.name)}
                    className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                      on
                        ? "bg-surface-3 text-cyan-300 border-cyan-700"
                        : "border-slate-700 text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    {on ? "✓ " : ""}{t.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Thread */}
          <div className="flex-1 overflow-y-auto px-6 py-6">
            <div className="max-w-3xl mx-auto space-y-8">
              {messages.length === 0 && !running && (
                <div className="text-center text-slate-500 mt-20">
                  <p className="text-lg text-slate-400 mb-2">Convene your research panel</p>
                  <p className="text-sm">Pick agents above, ask a question, and they’ll debate and synthesize an answer.</p>
                </div>
              )}
              {messages.map((m, i) =>
                m.kind === "user" ? (
                  <div key={i} className="flex justify-end">
                    <div className="bg-primary-700 text-white rounded-2xl rounded-br-sm px-4 py-2 max-w-[80%]">
                      {m.text}
                    </div>
                  </div>
                ) : (
                  <AssistantTurnView key={i} result={m.result} />
                )
              )}
              {running && (
                <div className="flex items-center gap-2 text-slate-400 text-sm">
                  <span className="animate-pulse">●</span> The panel is deliberating…
                </div>
              )}
              <div ref={endRef} />
            </div>
          </div>

          {/* Composer */}
          <div className="border-t border-surface-3 px-6 py-4 bg-surface-2/50">
            <div className="max-w-3xl mx-auto">
              {error && <p className="text-red-400 text-sm mb-2">{error}</p>}
              <div className="flex items-end gap-2">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={onKeyDown}
                  rows={1}
                  placeholder="Ask the panel… (Enter to send, Shift+Enter for newline)"
                  className="flex-1 resize-none bg-surface-3 border border-slate-600 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 max-h-40"
                />
                <button
                  onClick={send}
                  disabled={running || !input.trim()}
                  className="bg-primary-600 hover:bg-primary-700 text-white px-5 py-3 rounded-xl font-medium transition-colors disabled:opacity-50"
                >
                  {running ? "…" : "Send"}
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
