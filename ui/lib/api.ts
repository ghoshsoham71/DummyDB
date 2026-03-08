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

async function apiFetch<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.message || `Request failed: ${res.statusText}`);
  }
  return res.json();
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
