export type ListStatus =
  | "draft"
  | "queued"
  | "processing"
  | "paused"
  | "completed"
  | "cancelled"
  | "failed"
  | "interrupted";

export type RowStatus =
  | "pending"
  | "processing"
  | "verified"
  | "risky"
  | "failed"
  | "skipped";

export interface List {
  id: string;
  name: string;
  filename: string | null;
  status: ListStatus;
  email_column: string | null;
  total_rows: number;
  processed_rows: number;
  verified_count: number;
  risky_count: number;
  failed_count: number;
  skipped_count: number;
  settings_snapshot: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
}

export interface ListRow {
  row_index: number;
  email: string;
  status: RowStatus;
  reason: string | null;
  raw_row: Record<string, string>;
  checked_at: string | null;
}

export interface Settings {
  concurrency: number;
  timeout_seconds: number;
  retry_count: number;
  smtp_helo_domain: string;
  chunk_time_budget_seconds: number;
  theme: "dark" | "light";
  max_upload_size_mb: number;
}

export interface Stats {
  total_emails_verified: number;
  total_lists_completed: number;
  total_lists: number;
}

export interface ProgressEvent {
  processed: number;
  total: number;
  verified: number;
  risky: number;
  failed: number;
  status: ListStatus;
}

export interface ApiError {
  error: string;
  message: string;
  columns?: string[];
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as ApiError;
    const err = new Error(body.message || body.error || res.statusText) as Error & ApiError;
    err.error = body.error;
    err.columns = body.columns;
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; database: string }>("/health"),

  getStats: () => request<Stats>("/api/stats"),

  getSettings: () => request<Settings>("/api/settings"),

  updateSettings: (data: Partial<Settings>) =>
    request<Settings>("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  getLists: (params?: { status?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    const qs = q.toString();
    return request<{ lists: List[]; total: number }>(`/api/lists${qs ? `?${qs}` : ""}`);
  },

  createList: (name: string) =>
    request<List>("/api/lists", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }),

  getList: (id: string) => request<List>(`/api/lists/${id}`),

  deleteList: (id: string) =>
    request<void>(`/api/lists/${id}`, { method: "DELETE" }),

  uploadCsv: (id: string, file: File, emailColumn?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (emailColumn) form.append("email_column", emailColumn);
    return request<{
      list_id: string;
      filename: string;
      total_rows: number;
      email_column: string;
      estimated_duration: string;
      columns: string[];
    }>(`/api/lists/${id}/upload`, { method: "POST", body: form });
  },

  verifyList: (id: string) =>
    request<{ id: string; status: string; queue_position: number }>(
      `/api/lists/${id}/verify`,
      { method: "POST" }
    ),

  pauseList: (id: string) =>
    request<{ status: string }>(`/api/lists/${id}/pause`, { method: "POST" }),

  resumeList: (id: string) =>
    request<{ status: string }>(`/api/lists/${id}/resume`, { method: "POST" }),

  cancelList: (id: string) =>
    request<{ status: string }>(`/api/lists/${id}/cancel`, { method: "POST" }),

  getListRows: (
    id: string,
    params?: { status?: string; search?: string; limit?: number; offset?: number }
  ) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.search) q.set("search", params.search);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    const qs = q.toString();
    return request<{ rows: ListRow[]; total: number; limit: number; offset: number }>(
      `/api/lists/${id}/rows${qs ? `?${qs}` : ""}`
    );
  },

  exportUrl: (id: string, filter: "all" | "risky_failed" = "all") =>
    `/api/lists/${id}/export?filter=${filter}`,

  verifyEmail: (email: string) =>
    request<{ email: string; status: string; reason: string; message: string }>(
      "/verify-email",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      }
    ),

  findEmail: (name: string, website: string) =>
    request<{
      name: string;
      website: string;
      domain: string;
      found: boolean;
      valid_email: string | null;
      best_guess?: string;
      total_permutations: number;
      permutations_tested: { email: string; status: string; reason: string }[];
    }>("/find-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, website }),
    }),

  findEmailCompany: (domain: string) =>
    request<{
      domain: string;
      found: boolean;
      best_email: string | null;
      emails_tested: { email: string; status: string; reason: string }[];
    }>("/find-email/company", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domain }),
    }),
};

export function subscribeProgress(
  listId: string,
  onEvent: (event: ProgressEvent, type: "progress" | "complete") => void,
  onError?: () => void
): () => void {
  const source = new EventSource(`/api/lists/${listId}/progress`);

  source.addEventListener("progress", (e) => {
    onEvent(JSON.parse(e.data) as ProgressEvent, "progress");
  });

  source.addEventListener("complete", (e) => {
    onEvent(JSON.parse(e.data) as ProgressEvent, "complete");
    source.close();
  });

  source.onerror = () => {
    onError?.();
    source.close();
  };

  return () => source.close();
}
