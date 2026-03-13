import { supabase } from "./supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/* ─── Types ─── */

export interface TableAttribute {
  name: string;
  type: string;
  constraints: string[];
  type_params?: string;
}

export interface Table {
  name: string;
  attributes: TableAttribute[];
  node_type?: string;        // "node" | "relationship" (Neo4j)
  label?: string;
  relationships?: { type: string; target: string }[];
  document_count?: number;    // MongoDB
  node_count?: number;        // Neo4j
  relationship_count?: number;
}

export interface Database {
  name: string;
  tables: Table[];
}

export interface ParsedSchema {
  databases: Database[];
  source?: string;            // "mongodb" | "neo4j" | undefined (SQL)
  connection?: { uri?: string; http_browser?: string };
}

export interface SchemaListItem {
  schema_id: string;
  filename: string;
  created_at: string;
  file_size: number;
  table_count: number;
  content_hash: string;
}

export interface GenerationTemplate {
  name: string;
  description: string;
  scale_factor: number;
  synthesizer_type: string;
  recommended_for: string;
}

export interface JobItem {
  job_id: string;
  job_type: string;
  status: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  progress: number;
  message: string;
  parameters: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: string | null;
}

export interface StatsResponse {
  job_statistics: Record<string, unknown>;
  storage_statistics: Record<string, unknown>;
  synthetic_files: {
    total_files: number;
    total_size: number;
    recent_files: unknown[];
  };
  system_health: {
    job_queue_size: number;
    active_generations: number;
    failed_generations: number;
  };
}

export interface DashboardOverview {
  schemas: { total: number; total_tables: number; by_source: Record<string, number> };
  jobs: Record<string, unknown>;
  storage: Record<string, unknown>;
  synthetic_files: { total: number; total_size: number };
  timestamp: string;
}

export interface ActivityEvent {
  type: string;
  id: string;
  source: string;
  timestamp: number | string;
  filename?: string;
  message?: string;
}

/* ─── Helpers ─── */

export async function apiFetch<T>(path: string, opts?: RequestInit): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession();

  const headers = new Headers(opts?.headers || {});
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...opts,
    headers,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.message || `Request failed: ${res.statusText}`);
  }
  return res.json();
}

export async function deleteAccount() {
  return apiFetch<{ message: string }>("/auth/me", { method: "DELETE" });
}

export async function checkUsernameAvailable(username: string): Promise<{ available: boolean }> {
  try {
    return await apiFetch<{ available: boolean }>(`/auth/check-username?username=${encodeURIComponent(username)}`, { method: "GET" });
  } catch (error) {
    // If the check fails for any reason (e.g. backend down), return false for safety
    console.error("Failed to check username availability", error);
    return { available: false };
  }
}

/* ─── Schema Endpoints ─── */

export async function parseSQL(file: File, seedFile?: File) {
  const fd = new FormData();
  fd.append("file", file);
  if (seedFile) fd.append("seed_data_file", seedFile);
  return apiFetch<Record<string, unknown>>("/parse?save_to_disk=true&overwrite_existing=true", {
    method: "POST",
    body: fd,
  });
}

export async function parseSupabase(connectionString: string) {
  return apiFetch<Record<string, unknown>>("/parse/supabase", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ connection_string: connectionString, save_to_disk: true, overwrite_existing: true }),
  });
}

export async function parseMongoDB(connectionString: string, databaseName?: string, sampleSize = 100) {
  return apiFetch<Record<string, unknown>>("/parse/mongodb", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      connection_string: connectionString,
      database_name: databaseName || null,
      sample_size: sampleSize,
      save_to_disk: true,
      overwrite_existing: true,
    }),
  });
}

export async function parseJsonSchema(schema: Record<string, unknown>, filename = "schema.json") {
  return apiFetch<Record<string, unknown>>("/parse/json", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ schema, filename, save_to_disk: true, overwrite_existing: true }),
  });
}

export async function parseNeo4j(uri: string, username: string, password: string, database?: string) {
  return apiFetch<Record<string, unknown>>("/parse/neo4j", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      uri,
      username,
      password,
      database: database || null,
      save_to_disk: true,
      overwrite_existing: true,
    }),
  });
}

export async function listSchemas(limit = 50, offset = 0) {
  return apiFetch<{ schemas: SchemaListItem[]; total: number }>(
    `/schemas?limit=${limit}&offset=${offset}`
  );
}

export async function getSchema(schemaId: string) {
  return apiFetch<Record<string, unknown>>(`/schemas/${schemaId}`);
}

export async function deleteSchema(schemaId: string) {
  return apiFetch<{ message: string }>(`/schemas/${schemaId}`, { method: "DELETE" });
}

export async function bulkDeleteSchemas(schemaIds: string[]) {
  return apiFetch<{ message: string }>("/schemas/bulk-delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ schema_ids: schemaIds }),
  });
}

export async function getTableDetail(schemaId: string, tableName: string) {
  return apiFetch<Record<string, unknown>>(`/schemas/${schemaId}/tables/${tableName}`);
}

/* ─── Synthetic Data Endpoints ─── */

export interface GeneratePayload {
  schema_id: string;
  scale_factor?: number;
  num_rows?: Record<string, number>;
  synthesizer_type?: string;
  output_format?: string;
  seed?: number;
}

export async function generateSyntheticData(payload: GeneratePayload) {
  return apiFetch<{ success: boolean; generation_id: string; message: string }>(
    "/synthetic/generate",
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) },
  );
}

export interface StreamEvent {
  event: "start" | "table_start" | "table_done" | "error" | "complete";
  total_tables?: number;
  table?: string;
  rows_requested?: number;
  rows_generated?: number;
  index?: number;
  message?: string;
  file_paths?: string[];
  summary?: Record<string, { rows: number; columns: number }>;
}

export async function generateSyntheticDataStream(
  payload: GeneratePayload,
  onEvent: (evt: StreamEvent) => void,
) {
  const { data: { session } } = await supabase.auth.getSession();
  const headers = new Headers({ "Content-Type": "application/json" });
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }

  const res = await fetch(`${API_BASE}/synthetic/generate/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.statusText}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const evt: StreamEvent = JSON.parse(line.slice(6));
          onEvent(evt);
        } catch { /* skip malformed */ }
      }
    }
  }
}

export async function getJobStatus(jobId: string) {
  return apiFetch<JobItem>(`/synthetic/jobs/${jobId}/status`);
}

export async function listJobs(limit = 50, offset = 0) {
  return apiFetch<{ jobs: JobItem[]; total_jobs: number }>(
    `/synthetic/jobs?limit=${limit}&offset=${offset}`
  );
}

export async function cancelJob(jobId: string) {
  return apiFetch<{ message: string }>(`/synthetic/jobs/${jobId}`, { method: "DELETE" });
}

export function getDownloadUrl(generationId: string) {
  return `${API_BASE}/synthetic/download/${generationId}`;
}

export async function getTemplates() {
  return apiFetch<{ templates: Record<string, GenerationTemplate> }>("/synthetic/templates");
}

export interface RateLimitInfo {
  requests_per_minute: number;
  token_bucket_size: number;
  token_refill_per_sec: number;
  max_concurrent_calls: number;
  max_tables_per_request: number;
  max_rows_per_table: number;
  seed_data_bypasses: boolean;
}

export async function getRateLimits() {
  return apiFetch<RateLimitInfo>("/synthetic/rate-limits");
}

export async function getStats() {
  return apiFetch<StatsResponse>("/synthetic/stats");
}

export async function getHealth() {
  return apiFetch<Record<string, unknown>>("/health");
}

/* ─── Dashboard Endpoints ─── */

export async function getDashboardOverview() {
  return apiFetch<DashboardOverview>("/dashboard/overview");
}

export async function getDashboardActivity(limit = 20) {
  return apiFetch<{ events: ActivityEvent[]; total: number }>(`/dashboard/activity?limit=${limit}`);
}

export async function getDashboardSchemaStats() {
  return apiFetch<{ schemas: Record<string, unknown>[]; total_schemas: number; distribution: Record<string, number> }>(
    "/dashboard/schema-stats"
  );
}
