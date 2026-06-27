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
}

export interface WorkflowResult {
  hypothesis: Hypothesis;
  evidence_summary: string;
  retrieved_paper_count: number;
}
