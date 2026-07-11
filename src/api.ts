/**
 * Typed fetch helpers for the FastAPI backend.
 */

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export interface FindingScore {
  label: string;
  score: number;
}

export interface SimilarCase {
  uid: string;
  findings: string | null;
  impression: string | null;
  similarity: number;
}

export interface AnalyzeResponse {
  id: number;
  filename: string;
  top_finding: string;
  top_score: number;
  findings: FindingScore[];
  heatmap_url: string;
  thumbnail_url: string;
  priority: string;
  status: string;
  similar_cases: SimilarCase[];
  explanation: string;
  disclaimer: string;
  created_at: string;
}

export interface CaseSummary {
  id: number;
  filename: string;
  top_finding: string;
  top_score: number;
  findings?: FindingScore[];
  thumbnail_url: string;
  priority: string;
  status: string;
  review_reason?: "low_confidence" | "multiple_findings" | null;
  created_at: string;
}

export interface CaseDetail extends AnalyzeResponse {}

export async function analyzeImage(file: File): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/analyze`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Analysis failed");
  }
  return res.json();
}

export async function fetchQueue(status?: string): Promise<CaseSummary[]> {
  const url = status ? `${BASE}/api/queue?status=${status}` : `${BASE}/api/queue`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to load queue");
  return res.json();
}

export async function fetchCase(id: number): Promise<CaseDetail> {
  const res = await fetch(`${BASE}/api/queue/${id}`);
  if (res.status === 404) throw new Error("NOT_FOUND");
  if (!res.ok) throw new Error("Failed to load case");
  return res.json();
}

export async function markReviewed(id: number): Promise<CaseDetail> {
  const res = await fetch(`${BASE}/api/queue/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: "reviewed" }),
  });
  if (!res.ok) throw new Error("Failed to update case");
  return res.json();
}

export async function deleteCase(id: number): Promise<void> {
  const res = await fetch(`${BASE}/api/queue/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete case");
}
