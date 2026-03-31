const AR_API_BASE_URL =
  typeof process !== "undefined"
    ? process.env.NEXT_PUBLIC_AR_API_URL ?? "http://localhost:8000"
    : "http://localhost:8000";

export type ConversationMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  payload?: Record<string, unknown> | null;
  created_at: string;
};

export type ConversationSummary = {
  id: number;
  title: string | null;
  created_at: string;
  updated_at: string | null;
};

export type ConversationDetail = ConversationSummary & {
  messages: ConversationMessage[];
};

type ArEnvelope<T> = {
  status_code: number;
  message: string;
  data: T;
};

export async function getConversations(
  token: string,
): Promise<ConversationSummary[]> {
  const res = await fetch(`${AR_API_BASE_URL}/conversations`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const json = (await res.json()) as ArEnvelope<ConversationSummary[]>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function getConversation(
  token: string,
  conversationId: number,
): Promise<ConversationDetail> {
  const res = await fetch(
    `${AR_API_BASE_URL}/conversations/${conversationId}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  const json = (await res.json()) as ArEnvelope<ConversationDetail>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function createConversation(
  token: string,
  payload: {
    title?: string;
    user_message: string;
    assistant_message: string;
    assistant_payload?: Record<string, unknown>;
  },
): Promise<ConversationSummary> {
  const res = await fetch(`${AR_API_BASE_URL}/conversations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  const json = (await res.json()) as ArEnvelope<ConversationSummary>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function addConversationMessages(
  token: string,
  conversationId: number,
  payload: {
    user_message: string;
    assistant_message: string;
    assistant_payload?: Record<string, unknown>;
  },
): Promise<ConversationDetail> {
  const res = await fetch(
    `${AR_API_BASE_URL}/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    },
  );
  const json = (await res.json()) as ArEnvelope<ConversationDetail>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function deleteConversation(
  token: string,
  conversationId: number,
): Promise<void> {
  const res = await fetch(
    `${AR_API_BASE_URL}/conversations/${conversationId}`,
    {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    },
  );
  if (!res.ok) {
    const json = (await res.json()) as ArEnvelope<unknown>;
    throw new Error(json.message ?? `Request failed: ${res.status}`);
  }
}
