export type SearchChunk = {
  text: string;
  source_type: string;
  message_id?: string;
  message_url?: string;
  linked_url?: string;
  title?: string;
  score?: number;
};

export type SearchResponse = {
  chunks: SearchChunk[];
  answer?: string | null;
};

const API_BASE =
  (import.meta as any).env?.VITE_API_BASE?.toString() || "http://localhost:8000";

export async function createSession(): Promise<{ session_id: string }> {
  const res = await fetch(`${API_BASE}/api/sessions`, { method: "POST" });
  if (!res.ok) throw new Error(`createSession failed: ${res.status}`);
  return await res.json();
}

export async function search(query: string, top_k = 10, with_answer = false): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k, with_answer }),
  });
  if (!res.ok) throw new Error(`search failed: ${res.status}`);
  return await res.json();
}

