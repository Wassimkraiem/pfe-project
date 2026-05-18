export type AdminChatMode = "default" | "video_search";
type LegacyAdminChatMode = AdminChatMode | "chat";

export type AdminChatVideoResult = {
  video_id: string;
  title?: string;
  description?: string;
  thumbnail?: string;
};

export type AdminChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  videos?: AdminChatVideoResult[];
};

export type LocalAdminConversation = {
  id: number;
  title: string | null;
  created_at: string;
  updated_at: string | null;
  mode: AdminChatMode;
  messages: AdminChatMessage[];
};

const STORAGE_KEY = "arp-admin-chat-history-v1";

function hasWindow(): boolean {
  return typeof window !== "undefined";
}

export function loadLocalAdminConversations(): LocalAdminConversation[] {
  if (!hasWindow()) return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(
        (item): item is Omit<LocalAdminConversation, "mode"> & { mode?: LegacyAdminChatMode } =>
          !!item &&
          typeof item === "object" &&
          typeof (item as LocalAdminConversation).id === "number" &&
          Array.isArray((item as LocalAdminConversation).messages),
      )
      .map((item) => ({
        ...item,
        mode: item.mode === "video_search" ? "video_search" : "default",
      }));
  } catch {
    return [];
  }
}

export function saveLocalAdminConversations(items: LocalAdminConversation[]): void {
  if (!hasWindow()) return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

export function upsertLocalAdminConversation(
  conversation: LocalAdminConversation,
): LocalAdminConversation[] {
  const current = loadLocalAdminConversations();
  const next = [
    conversation,
    ...current.filter((item) => item.id !== conversation.id),
  ].sort((a, b) => {
    const left = new Date(b.updated_at ?? b.created_at).getTime();
    const right = new Date(a.updated_at ?? a.created_at).getTime();
    return left - right;
  });
  saveLocalAdminConversations(next);
  return next;
}

export function deleteLocalAdminConversation(id: number): LocalAdminConversation[] {
  const next = loadLocalAdminConversations().filter((item) => item.id !== id);
  saveLocalAdminConversations(next);
  return next;
}

export function createLocalAdminConversation(input: {
  title?: string | null;
  mode: AdminChatMode;
  messages: AdminChatMessage[];
}): LocalAdminConversation {
  const now = new Date().toISOString();
  return {
    id: Date.now(),
    title: input.title?.trim() || null,
    created_at: now,
    updated_at: now,
    mode: input.mode,
    messages: input.messages,
  };
}
