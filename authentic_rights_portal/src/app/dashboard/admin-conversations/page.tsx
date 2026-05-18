"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth, useUser } from "@clerk/nextjs";
import {
  Alert,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { MessageSquareText, UserRound } from "lucide-react";

import { getApiToken } from "@/lib/auth";
import { loadLocalAdminConversations } from "@/lib/adminChatHistory";
import {
  getAdminConversation,
  getAdminConversations,
  getConversation,
  getConversations,
  type AdminConversationDetail,
  type AdminConversationSummary,
  type ConversationDetail,
  type ConversationSummary,
} from "@/lib/api";

type ConversationScope = "admin" | "self" | "local";

function formatDate(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function getOwnerLabel(conversation: AdminConversationSummary): string {
  const first = conversation.user?.first_name?.trim();
  const last = conversation.user?.last_name?.trim();
  const full = [first, last].filter(Boolean).join(" ").trim();
  return full || conversation.user?.email?.trim() || "Unknown user";
}

function toSelfScopedSummary(
  conversations: ConversationSummary[],
  userEmail?: string | null,
  firstName?: string | null,
  lastName?: string | null,
): AdminConversationSummary[] {
  return conversations.map((conversation) => ({
    ...conversation,
    message_count: undefined,
    last_message_at: conversation.updated_at ?? conversation.created_at,
    user: {
      email: userEmail ?? undefined,
      first_name: firstName ?? undefined,
      last_name: lastName ?? undefined,
    },
  }));
}

function toSelfScopedDetail(
  detail: ConversationDetail,
  summary: AdminConversationSummary | undefined,
): AdminConversationDetail {
  return {
    ...detail,
    user: summary?.user,
    message_count: detail.messages.length,
    last_message_at:
      detail.messages.length > 0
        ? detail.messages[detail.messages.length - 1]?.created_at ?? detail.updated_at
        : detail.updated_at ?? detail.created_at,
  };
}

function isUserNotFoundError(err: unknown): boolean {
  if (!(err instanceof Error)) return false;
  const value = err.message.toLowerCase();
  return value.includes("user not found") || value.includes("user_not_found");
}

export default function AdminConversationsPage() {
  const { getToken } = useAuth();
  const { user } = useUser();
  const [scope, setScope] = useState<ConversationScope>("admin");
  const [items, setItems] = useState<AdminConversationSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedConversation, setSelectedConversation] =
    useState<AdminConversationDetail | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const loadConversations = useCallback(async () => {
    setLoadingList(true);
    setError(null);
    setNotice(null);
    try {
      const token = await getApiToken(getToken);
      if (!token) throw new Error("Missing auth token.");

      try {
        const adminItems = await getAdminConversations(token);
        setItems(adminItems);
        setScope("admin");
        if (adminItems.length > 0) {
          setSelectedId((current) => current ?? adminItems[0].id);
        }
      } catch (adminErr) {
        try {
          const selfItems = await getConversations(token);
          const normalized = toSelfScopedSummary(
            selfItems,
            user?.primaryEmailAddress?.emailAddress ?? null,
            user?.firstName ?? null,
            user?.lastName ?? null,
          );
          setItems(normalized);
          setScope("self");
          setNotice(
            adminErr instanceof Error
              ? `Admin conversation API is unavailable. Showing only your own saved conversations for now: ${adminErr.message}`
              : "Admin conversation API is unavailable. Showing only your own saved conversations for now.",
          );
          if (normalized.length > 0) {
            setSelectedId((current) => current ?? normalized[0].id);
          }
        } catch (selfErr) {
          const localItems = loadLocalAdminConversations().map((conversation) => ({
            id: conversation.id,
            title: conversation.title,
            created_at: conversation.created_at,
            updated_at: conversation.updated_at,
            last_message_at: conversation.updated_at ?? conversation.created_at,
            message_count: conversation.messages.length,
            user: {
              email: user?.primaryEmailAddress?.emailAddress ?? undefined,
              first_name: user?.firstName ?? undefined,
              last_name: user?.lastName ?? undefined,
            },
          }));
          setItems(localItems);
          setScope("local");
          setNotice(
            isUserNotFoundError(selfErr)
              ? "Global admin conversations are not exposed by the backend yet, and this admin account is not in the AR database. Showing local admin test history instead."
              : "Global admin conversations are unavailable right now. Showing local admin test history instead.",
          );
          if (localItems.length > 0) {
            setSelectedId((current) => current ?? localItems[0].id);
          }
        }
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load conversations.",
      );
    } finally {
      setLoadingList(false);
    }
  }, [getToken, user?.firstName, user?.lastName, user?.primaryEmailAddress?.emailAddress]);

  const loadConversationDetail = useCallback(
    async (conversationId: number) => {
      setSelectedId(conversationId);
      setLoadingDetail(true);
      setError(null);
      try {
        const token = await getApiToken(getToken);
        if (!token) throw new Error("Missing auth token.");

        if (scope === "admin") {
          const detail = await getAdminConversation(token, conversationId);
          setSelectedConversation(detail);
        } else if (scope === "self") {
          const detail = await getConversation(token, conversationId);
          const summary = items.find((item) => item.id === conversationId);
          setSelectedConversation(toSelfScopedDetail(detail, summary));
        } else {
          const local = loadLocalAdminConversations().find((item) => item.id === conversationId);
          if (!local) throw new Error("Local admin conversation not found.");
          setSelectedConversation({
            id: local.id,
            title: local.title,
            created_at: local.created_at,
            updated_at: local.updated_at,
            last_message_at: local.updated_at ?? local.created_at,
            message_count: local.messages.length,
            user: {
              email: user?.primaryEmailAddress?.emailAddress ?? undefined,
              first_name: user?.firstName ?? undefined,
              last_name: user?.lastName ?? undefined,
            },
            messages: local.messages.map((message, index) => ({
              id: index + 1,
              role: message.role,
              content: message.content,
              created_at: local.updated_at ?? local.created_at,
            })),
          });
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load conversation detail.",
        );
      } finally {
        setLoadingDetail(false);
      }
    },
    [getToken, items, scope, user?.firstName, user?.lastName, user?.primaryEmailAddress?.emailAddress],
  );

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    if (!selectedId) return;
    loadConversationDetail(selectedId);
  }, [loadConversationDetail, selectedId]);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      const haystack = [
        item.title ?? "",
        item.user?.email ?? "",
        item.user?.first_name ?? "",
        item.user?.last_name ?? "",
      ]
        .join(" ")
        .toLowerCase();
      return !search.trim() || haystack.includes(search.trim().toLowerCase());
    });
  }, [items, search]);

  return (
    <Box>
      <Box>
        <Typography fontSize={28} fontWeight={800} color="#111827">
          User Conversations
        </Typography>
        <Typography fontSize={14} color="text.secondary" sx={{ mt: 0.75 }}>
          Browse chatbot conversations, inspect message history, and see how users are interacting with the assistant.
        </Typography>
      </Box>

      {notice ? (
        <Alert severity="info" sx={{ mt: 2 }}>
          {notice}
        </Alert>
      ) : null}

      {error ? (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      ) : null}

      <Box
        sx={{
          mt: 3,
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "340px minmax(0, 1fr)" },
          gap: 2,
        }}
      >
        <Card variant="outlined" sx={{ borderRadius: 3, borderColor: "#e5e7eb" }}>
          <CardContent sx={{ p: 0 }}>
            <Box sx={{ px: 2.5, py: 2 }}>
              <Typography fontSize={16} fontWeight={700}>
                Conversation Index
              </Typography>
              <Typography fontSize={12} color="text.secondary" sx={{ mt: 0.5 }}>
                Scope: {scope === "admin" ? "all users" : scope === "self" ? "your account only" : "local admin test history"}
              </Typography>
              <TextField
                fullWidth
                size="small"
                label="Search"
                placeholder="Title or user"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                sx={{ mt: 1.5 }}
              />
            </Box>
            <Divider />
            {loadingList ? (
              <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                <CircularProgress size={22} sx={{ color: "#4D8AFF" }} />
              </Box>
            ) : filteredItems.length === 0 ? (
              <Box sx={{ px: 2.5, py: 4 }}>
                <Typography fontSize={13} color="text.secondary">
                  No conversations match the current search.
                </Typography>
              </Box>
            ) : (
              <Box sx={{ maxHeight: { lg: 700 }, overflowY: "auto" }}>
                {filteredItems.map((item) => {
                  const active = item.id === selectedId;
                  return (
                    <Box
                      key={item.id}
                      onClick={() => loadConversationDetail(item.id)}
                      sx={{
                        px: 2.5,
                        py: 1.75,
                        cursor: "pointer",
                        borderBottom: "1px solid #f1f5f9",
                        bgcolor: active ? "#f8fbff" : "transparent",
                        "&:hover": { bgcolor: active ? "#f8fbff" : "#fafafa" },
                      }}
                    >
                      <Typography fontSize={13} fontWeight={700} noWrap>
                        {item.title || "Untitled conversation"}
                      </Typography>
                      <Typography fontSize={11} color="text.secondary" sx={{ mt: 0.5 }}>
                        {getOwnerLabel(item)}
                      </Typography>
                      <Typography fontSize={11} color="text.secondary" sx={{ mt: 0.25 }}>
                        Last activity: {formatDate(item.last_message_at ?? item.updated_at ?? item.created_at)}
                      </Typography>
                    </Box>
                  );
                })}
              </Box>
            )}
          </CardContent>
        </Card>

        <Card variant="outlined" sx={{ borderRadius: 3, borderColor: "#e5e7eb" }}>
          <CardContent sx={{ p: 0 }}>
            <Box sx={{ px: 2.5, py: 2, borderBottom: "1px solid #e5e7eb" }}>
              <Stack
                direction={{ xs: "column", md: "row" }}
                spacing={1.5}
                justifyContent="space-between"
              >
                <Box>
                  <Typography fontSize={18} fontWeight={800}>
                    Conversation Detail
                  </Typography>
                  <Typography fontSize={12} color="text.secondary" sx={{ mt: 0.5 }}>
                    Review the full transcript and identify what the assistant returned.
                  </Typography>
                </Box>
                {selectedConversation ? (
                  <Box
                    sx={{
                      alignSelf: { xs: "flex-start", md: "center" },
                      px: 1.25,
                      py: 0.85,
                      borderRadius: 999,
                      bgcolor: "#f8fafc",
                      border: "1px solid #e5e7eb",
                    }}
                  >
                    <Typography fontSize={12} fontWeight={700}>
                      {selectedConversation.message_count ?? selectedConversation.messages.length} messages
                    </Typography>
                  </Box>
                ) : null}
              </Stack>
            </Box>

            {loadingDetail ? (
              <Box sx={{ display: "flex", justifyContent: "center", py: 10 }}>
                <CircularProgress size={24} sx={{ color: "#4D8AFF" }} />
              </Box>
            ) : !selectedConversation ? (
              <Box sx={{ px: 2.5, py: 8 }}>
                <Typography fontSize={13} color="text.secondary" align="center">
                  Select a conversation to inspect its transcript.
                </Typography>
              </Box>
            ) : (
              <Box sx={{ p: 2.5 }}>
                <Stack
                  direction={{ xs: "column", md: "row" }}
                  spacing={1.5}
                  justifyContent="space-between"
                >
                  <Box>
                    <Typography fontSize={18} fontWeight={800} color="#111827">
                      {selectedConversation.title || "Untitled conversation"}
                    </Typography>
                    <Typography fontSize={12} color="text.secondary" sx={{ mt: 0.5 }}>
                      Opened {formatDate(selectedConversation.created_at)}
                    </Typography>
                  </Box>
                  <Box
                    sx={{
                      display: "grid",
                      gap: 0.75,
                      minWidth: { md: 240 },
                      alignSelf: { xs: "flex-start", md: "start" },
                    }}
                  >
                    <Box
                      sx={{
                        p: 1.25,
                        borderRadius: 2,
                        bgcolor: "#f8fafc",
                        border: "1px solid #e5e7eb",
                      }}
                    >
                      <Stack direction="row" spacing={1} alignItems="center">
                        <UserRound style={{ width: 14, height: 14 }} />
                        <Typography fontSize={12} fontWeight={700}>
                          {getOwnerLabel(selectedConversation)}
                        </Typography>
                      </Stack>
                      {selectedConversation.user?.email ? (
                        <Typography fontSize={12} color="text.secondary" sx={{ mt: 0.5 }}>
                          {selectedConversation.user.email}
                        </Typography>
                      ) : null}
                    </Box>
                    <Box
                      sx={{
                        p: 1.25,
                        borderRadius: 2,
                        bgcolor: "#f8fafc",
                        border: "1px solid #e5e7eb",
                      }}
                    >
                      <Stack direction="row" spacing={1} alignItems="center">
                        <MessageSquareText style={{ width: 14, height: 14 }} />
                        <Typography fontSize={12} fontWeight={700}>
                          Last activity
                        </Typography>
                      </Stack>
                      <Typography fontSize={12} color="text.secondary" sx={{ mt: 0.5 }}>
                        {formatDate(
                          selectedConversation.last_message_at ??
                            selectedConversation.updated_at ??
                            selectedConversation.created_at,
                        )}
                      </Typography>
                    </Box>
                  </Box>
                </Stack>

                <Box sx={{ mt: 3, display: "flex", flexDirection: "column", gap: 1.25 }}>
                  {selectedConversation.messages.map((message) => {
                    const isUser = message.role === "user";
                    return (
                      <Box
                        key={message.id}
                        sx={{
                          alignSelf: isUser ? "flex-end" : "flex-start",
                          maxWidth: "90%",
                          px: 1.5,
                          py: 1.25,
                          borderRadius: 3,
                          bgcolor: isUser ? "#111827" : "#fff",
                          color: isUser ? "#fff" : "#111827",
                          border: isUser ? "none" : "1px solid #e5e7eb",
                          boxShadow: isUser
                            ? "0 18px 36px rgba(17,24,39,0.18)"
                            : "0 10px 28px rgba(15,23,42,0.06)",
                        }}
                      >
                        <Typography
                          fontSize={11}
                          fontWeight={800}
                          sx={{ mb: 0.5, opacity: isUser ? 0.9 : 0.7 }}
                        >
                          {isUser ? "USER" : "ASSISTANT"}
                        </Typography>
                        <Typography fontSize={14} sx={{ whiteSpace: "pre-wrap" }}>
                          {message.content}
                        </Typography>
                        <Typography
                          fontSize={11}
                          sx={{ mt: 1, opacity: isUser ? 0.85 : 0.6 }}
                        >
                          {formatDate(message.created_at)}
                        </Typography>
                      </Box>
                    );
                  })}
                </Box>
              </Box>
            )}
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}
