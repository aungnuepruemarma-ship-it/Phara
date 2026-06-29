export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "researcher";
  is_active: boolean;
  created_at: string;
}

export interface Project {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface Paper {
  id: string;
  project_id: string;
  title: string;
  authors: string[];
  abstract: string | null;
  year: number | null;
  doi: string | null;
  file_path: string;
  embedding_status: "pending" | "done" | "failed";
  chunk_count: number;
  uploaded_at: string;
}

export interface Experiment {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  parameters: Record<string, unknown>;
  status: "draft" | "running" | "completed" | "failed";
  results: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  hypotheses?: Hypothesis[];
}

export interface Note {
  id: string;
  project_id: string;
  author_id: string;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export type HypothesisReviewStatus = "candidate" | "under_review" | "accepted" | "rejected";

export interface Hypothesis {
  id: string;
  experiment_id: string;
  question: string;
  retrieved_paper_ids: string[];
  evidence_summary: string;
  hypothesis_text: string;
  agent_used: string;
  confidence_score: number | null;
  created_at: string;
  // Blueprint v1.0: every hypothesis is a candidate until reviewed
  review_status: HypothesisReviewStatus;
  review_notes: string | null;
  reviewed_at: string | null;
}

export interface AgentMemory {
  id: string;
  project_id: string;
  agent_name: string;
  memory_type: string;
  content: string;
  source_question: string;
  tags: string[];
  created_at: string;
}

export interface DebateEntry {
  role: string;
  hypothesis: string;
  reasoning: string;
  confidence: number;
}

export interface ContradictionItem {
  claim_a: string;
  source_a: number;
  claim_b: string;
  source_b: number;
  explanation: string;
  severity: "high" | "medium" | "low";
}

export interface ToolSpec {
  name: string;
  description: string;
  category: "research" | "memory" | "analysis" | "utility";
  input_schema: Record<string, unknown>;
}

export interface ToolResult {
  tool_name: string;
  success: boolean;
  output: any;
  error: string | null;
  elapsed_ms: number;
}

export interface WorkflowResult {
  hypothesis: Hypothesis;
  evidence_summary: string;
  retrieved_paper_count: number;
  debate: DebateEntry[];
  critique: DebateEntry | null;
  contradictions: ContradictionItem[];
  mlflow_run_id: string | null;
  tool_results: ToolResult[];
}

export interface AgentTurn {
  agent_name: string;
  role: "perspective" | "rebuttal" | "synthesis" | "experiment";
  content: string;
  confidence: number;
}

export interface DomainPatternOut {
  pattern_type: string;
  description: string;
  domains_seen: string[];
  confidence: number;
}

export interface RoundtableResult {
  turns: AgentTurn[];
  final_text: string;
  final_confidence: number;
  patterns: DomainPatternOut[];
  tool_results: ToolResult[];
  saved_hypothesis_id: string | null;
  retrieved_paper_count: number;
}

export interface ProjectReport {
  project_id: string;
  project_name: string;
  generated_at: string;
  experiment_count: number;
  hypothesis_count: number;
  hypotheses: {
    id: string;
    question: string;
    hypothesis_text: string;
    agent_used: string;
    confidence_score: number | null;
    created_at: string;
  }[];
  synthesis: string;
  top_agents: string[];
  avg_confidence: number | null;
}

export interface TrackingRun {
  run_id: string;
  start_time: string | null;
  status: string | null;
  params: Record<string, string>;
  metrics: Record<string, number>;
  tags: Record<string, string>;
}

export interface KGEntity {
  id: string;
  name: string;
  entity_type: string;
  domain: string;
  description: string | null;
  confidence: number;
  source_hypothesis_id: string | null;
  created_at?: string;
}

export interface KGEdge {
  id: string;
  source: string;
  target: string;
  relation_type: string;
  evidence_text: string | null;
  confidence: number;
}

export interface GraphData {
  nodes: KGEntity[];
  edges: KGEdge[];
}

export interface KGAnalogy {
  relation_id: string;
  entity_a: { id: string; name: string; domain: string };
  entity_b: { id: string; name: string; domain: string };
  explanation: string | null;
  confidence: number;
}

export interface DimensionScore {
  name: string;
  score: number;
  reasoning: string;
}

export interface BenchmarkScore {
  name: string;
  score: number;
  details: Record<string, unknown>;
}

export interface EvaluationOut {
  id: string;
  hypothesis_id: string;
  project_id: string;
  overall_score: number;
  verdict: "strong" | "moderate" | "weak";
  dimension_scores: DimensionScore[];
  benchmark_scores: BenchmarkScore[];
  created_at: string;
}

export interface EvaluationSummary {
  project_id: string;
  hypothesis_count: number;
  avg_score: number | null;
  best_agent: string | null;
  score_trend: number[];
}

export interface SimulationVariantIn {
  name: string;
  agent_name: string;
  enable_debate: boolean;
  enable_critique: boolean;
  enable_contradiction_check: boolean;
  ablate_retrieval: boolean;
  ablate_memory: boolean;
  ablate_kg: boolean;
  ablate_tools: boolean;
  adversarial_context: string[];
  retrieval_top_k: number | null;
}

export interface SimulationRequest {
  simulation_type: "agent_sweep" | "parameter_sweep" | "stability_test";
  question: string;
  experiment_id?: string;
  variants: SimulationVariantIn[];
  runs_per_variant: number;
}

export interface VariantResultOut {
  id: string;
  variant_name: string;
  agent_name: string;
  run_index: number;
  hypothesis_id: string | null;
  evaluation_score: number | null;
  verdict: string | null;
  dimension_scores: { name: string; score: number; reasoning: string }[];
  full_state: Record<string, unknown> | null;
  created_at: string;
}

export interface SimulationOut {
  id: string;
  project_id: string;
  experiment_id: string | null;
  simulation_type: string;
  question: string;
  status: "pending" | "running" | "completed" | "failed";
  best_variant: string | null;
  summary: Record<string, { mean: number; std: number; runs: number } | string> | null;
  variant_results: VariantResultOut[];
  created_at: string;
  updated_at: string;
}
