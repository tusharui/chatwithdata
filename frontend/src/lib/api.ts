const API_BASE = "";

interface RequestOptions {
  method?: string;
  body?: unknown;
  token?: string;
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, token } = options;

  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body) headers["Content-Type"] = "application/json";

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000);

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    clearTimeout(timeout);

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const error = await res.json();
        detail = error.detail || detail;
      } catch {}
      throw new Error(detail);
    }

    return res.json();
  } catch (err) {
    clearTimeout(timeout);
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Request timed out. Please try again.");
    }
    if (err instanceof TypeError && (err as Error).message === "Failed to fetch") {
      throw new Error("Cannot connect to server.");
    }
    throw err;
  }
}

async function uploadFile<T>(endpoint: string, file: File, extraFields: Record<string, string> = {}, token?: string): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);
  Object.entries(extraFields).forEach(([key, value]) => {
    formData.append(key, value);
  });

  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 300000);

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers,
      body: formData,
      signal: controller.signal,
    });

    clearTimeout(timeout);

    if (!res.ok) {
      let detail = `Upload failed (HTTP ${res.status})`;
      try {
        const error = await res.json();
        detail = error.detail || detail;
      } catch {}
      throw new Error(detail);
    }

    return res.json();
  } catch (err) {
    clearTimeout(timeout);
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Upload timed out.");
    }
    throw err;
  }
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      request<{ access_token: string; user: { id: string; email: string; name: string } }>("/api/auth/login", {
        method: "POST",
        body: { email, password },
      }),
    register: (email: string, name: string, password: string) =>
      request<{ access_token: string; user: { id: string; email: string; name: string } }>("/api/auth/register", {
        method: "POST",
        body: { email, name, password },
      }),
    me: (token: string) =>
      request<{ id: string; email: string; name: string }>("/api/auth/me", { token }),
  },
  datasets: {
    list: (token: string) =>
      request<{ datasets: Array<{ id: string; name: string; filename: string; row_count: number; column_count: number; status: string; created_at: string; columns: unknown[] }>; total: number }>("/api/datasets/", { token }),
    get: (id: string, token: string) =>
      request<{ id: string; name: string; filename: string; row_count: number; column_count: number; table_name: string; status: string; created_at: string; columns: unknown[] }>(`/api/datasets/${encodeURIComponent(id)}`, { token }),
    upload: (file: File, name: string, description: string, token: string) =>
      uploadFile<{ id: string; name: string; filename: string; row_count: number; column_count: number; status: string; created_at: string; columns: unknown[] }>("/api/datasets/upload", file, { name, description }, token),
    delete: (id: string, token: string) =>
      request<{ message: string }>(`/api/datasets/${encodeURIComponent(id)}`, { method: "DELETE", token }),
  },
  chat: {
    send: (datasetId: string, message: string, conversationId: string | null, token: string) =>
      request<{ id: string; conversation_id: string; role: string; content: string; chart_type: string | null; chart_data: unknown; table_data: unknown; sql_query: string | null; created_at: string }>("/api/chat/", {
        method: "POST",
        body: { dataset_id: datasetId, message, conversation_id: conversationId },
        token,
      }),
    conversations: (datasetId: string, token: string) =>
      request<{ conversations: Array<{ id: string; title: string; messages: unknown[]; created_at: string }> }>(`/api/chat/conversations/${encodeURIComponent(datasetId)}`, { token }),
    get: (conversationId: string, token: string) =>
      request<{ id: string; title: string; messages: unknown[]; created_at: string }>(`/api/chat/conversation/${encodeURIComponent(conversationId)}`, { token }),
  },
};
