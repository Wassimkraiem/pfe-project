"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  ButtonGroup,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useAuth } from "@clerk/nextjs";
import { MessageSquare, Plus, Send, Trash2 } from "lucide-react";

import { getApiToken } from "@/lib/auth";
import {
  AdminChatMode,
  createLocalAdminConversation,
  deleteLocalAdminConversation,
  loadLocalAdminConversations,
  upsertLocalAdminConversation,
} from "@/lib/adminChatHistory";
import {
  addConversationMessages,
  ConversationSummary,
  createConversation,
  deleteConversation,
  getConversation,
  getConversations,
} from "@/lib/api";

type ChatRole = "user" | "assistant";

type VideoResult = {
  video_id: string;
  title?: string;
  description?: string;
  thumbnail?: string;
};

type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  videos?: VideoResult[];
};

type HistoryMode = "remote" | "local";

const CHAT_PROXY_URL = "/api/chat";
const VIDEOSEARCH_PORTAL_BASE_URL =
  process.env.NEXT_PUBLIC_VIDEOSEARCH_PORTAL_URL?.replace(/\/$/, "") ||
  "http://localhost:3002";

const WELCOME_MESSAGE: ChatMessage = {
  id: "admin-welcome",
  role: "assistant",
  content:
    "Admin test mode is ready. Ask about support, licensing, onboarding, or video search and the conversation will be saved to your own history.",
};

function buildVideoDetailsUrl(videoId: string): string {
  return `${VIDEOSEARCH_PORTAL_BASE_URL}/video/${encodeURIComponent(videoId)}`;
}

function extractAssistantReply(payload: unknown): string {
  if (typeof payload === "string") return payload;
  if (!payload || typeof payload !== "object") {
    return "I could not read a response from the assistant.";
  }

  const record = payload as Record<string, unknown>;
  const nested = (record.data ?? {}) as Record<string, unknown>;

  return (
    (record.answer as string) ??
    (record.reply as string) ??
    (record.response as string) ??
    (record.message as string) ??
    (nested.answer as string) ??
    (nested.reply as string) ??
    (nested.response as string) ??
    (nested.message as string) ??
    "I could not read a response from the assistant."
  );
}

function extractVideos(payload: unknown): VideoResult[] {
  if (!payload || typeof payload !== "object") return [];
  const record = payload as Record<string, unknown>;
  const videos = record.videos ?? (record.data as Record<string, unknown> | undefined)?.videos;
  if (!Array.isArray(videos)) return [];
  return videos.filter(
    (item): item is VideoResult =>
      !!item &&
      typeof item === "object" &&
      typeof (item as VideoResult).video_id === "string",
  );
}

function extractVideosFromMessagePayload(payload: unknown): VideoResult[] {
  if (!payload || typeof payload !== "object") return [];
  const videos = (payload as { videos?: unknown }).videos;
  if (!Array.isArray(videos)) return [];
  return videos.filter(
    (item): item is VideoResult =>
      !!item &&
      typeof item === "object" &&
      typeof (item as VideoResult).video_id === "string",
  );
}

function extractReplyFromMessagePayload(payload: unknown): string {
  if (!payload || typeof payload !== "object") return "";
  const reply = (payload as { reply?: unknown }).reply;
  return typeof reply === "string" ? reply : "";
}

function formatConversationLabel(conversation: ConversationSummary): string {
  const title = conversation.title?.trim();
  if (title) return title;
  return "Untitled conversation";
}

function buildConversationTitle(text: string): string {
  const trimmed = text.trim();
  return trimmed.length > 80 ? `${trimmed.slice(0, 77)}...` : trimmed;
}

function isUserNotFoundError(err: unknown): boolean {
  if (!(err instanceof Error)) return false;
  const value = err.message.toLowerCase();
  return value.includes("user not found") || value.includes("user_not_found");
}

export default function AdminChatConsole() {
  const { isLoaded, userId, getToken } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [chatMode, setChatMode] = useState<AdminChatMode>("default");
  const [isSending, setIsSending] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [loadingConversationId, setLoadingConversationId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyMode, setHistoryMode] = useState<HistoryMode>("remote");

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const isSignedIn = !!userId;

  const fetchToken = useCallback(async () => {
    if (!isSignedIn) return null;
    return getApiToken(getToken);
  }, [getToken, isSignedIn]);

  const loadConversations = useCallback(async () => {
    const token = await fetchToken();
    setLoadingHistory(true);
    setHistoryError(null);
    if (!token) {
      const localItems = loadLocalAdminConversations();
      setConversations(localItems);
      setHistoryMode("local");
      setLoadingHistory(false);
      return;
    }
    try {
      const items = await getConversations(token);
      setConversations(items);
      setHistoryMode("remote");
      if (items.length === 0 && !activeConversationId) {
        setMessages([WELCOME_MESSAGE]);
      }
    } catch (err) {
      const localItems = loadLocalAdminConversations();
      setConversations(localItems);
      setHistoryMode("local");
      setHistoryError(
        isUserNotFoundError(err)
          ? "This admin account is not provisioned in the AR database, so admin test history is running in local mode."
          : err instanceof Error
            ? `Remote history is unavailable, so admin test history is running in local mode: ${err.message}`
            : "Remote history is unavailable, so admin test history is running in local mode.",
      );
    } finally {
      setLoadingHistory(false);
    }
  }, [activeConversationId, fetchToken]);

  const loadConversation = useCallback(
    async (conversationId: number) => {
      setLoadingConversationId(conversationId);
      setError(null);
      try {
        if (historyMode === "local") {
          const local = loadLocalAdminConversations().find((item) => item.id === conversationId);
          if (!local) throw new Error("Local conversation not found.");
          setMessages(local.messages.length > 0 ? (local.messages as ChatMessage[]) : [WELCOME_MESSAGE]);
          setChatMode(local.mode);
          setActiveConversationId(conversationId);
        } else {
          const token = await fetchToken();
          if (!token) throw new Error("Missing auth token.");
          const detail = await getConversation(token, conversationId);
          const loaded: ChatMessage[] = detail.messages.map((message) => ({
            id: `db-${message.id}`,
            role: message.role,
            content:
              message.role === "assistant"
                ? message.content || extractReplyFromMessagePayload(message.payload)
                : message.content,
            videos:
              message.role === "assistant"
                ? extractVideosFromMessagePayload(message.payload)
                : undefined,
          }));
          setMessages(loaded.length > 0 ? loaded : [WELCOME_MESSAGE]);
          setActiveConversationId(conversationId);
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load this conversation.",
        );
      } finally {
        setLoadingConversationId(null);
      }
    },
    [fetchToken, historyMode],
  );

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    loadConversations();
  }, [isLoaded, isSignedIn, loadConversations]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isSending]);

  const startNewConversation = useCallback(() => {
    setActiveConversationId(null);
    setMessages([WELCOME_MESSAGE]);
    setInput("");
    setError(null);
  }, []);

  const handleDeleteConversation = useCallback(
    async (conversationId: number) => {
      try {
        if (historyMode === "local") {
          setConversations(deleteLocalAdminConversation(conversationId));
        } else {
          const token = await fetchToken();
          if (!token) throw new Error("Missing auth token.");
          await deleteConversation(token, conversationId);
          setConversations((prev) => prev.filter((item) => item.id !== conversationId));
        }
        if (activeConversationId === conversationId) {
          startNewConversation();
        }
      } catch (err) {
        setHistoryError(
          err instanceof Error ? err.message : "Failed to delete the conversation.",
        );
      }
    },
    [activeConversationId, fetchToken, historyMode, startNewConversation],
  );

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const text = input.trim();
      if (!text || isSending) return;

      const userMessage: ChatMessage = {
        id: `u-${Date.now()}`,
        role: "user",
        content: text,
      };
      const nextMessages = [...messages, userMessage];
      setMessages(nextMessages);
      setInput("");
      setIsSending(true);
      setError(null);

      try {
        const requestMode: "default" | "video_search" =
          chatMode === "video_search" ? "video_search" : "default";
        const response = await fetch(CHAT_PROXY_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            mode: requestMode,
            input_message: text,
            message: text,
            user_id: userId ?? "admin-anonymous",
            history: nextMessages.map((message) => ({
              role: message.role,
              content: message.content,
            })),
          }),
        });

        if (!response.ok) {
          throw new Error(`Chat API returned ${response.status}`);
        }

        const payload = (await response.json()) as unknown;
        const extractedReply = extractAssistantReply(payload);
        const extractedVideos = extractVideos(payload);
        const assistantText =
          extractedReply === "I could not read a response from the assistant." &&
          extractedVideos.length > 0
            ? `Found ${extractedVideos.length} videos for your request.`
            : extractedReply;

        const assistantMessage: ChatMessage = {
          id: `a-${Date.now()}`,
          role: "assistant",
          content: assistantText,
          videos: extractedVideos.length > 0 ? extractedVideos : undefined,
        };
        setMessages((current) => [...current, assistantMessage]);

        const token = await fetchToken();
        if (historyMode === "local" || !token) {
          const currentLocalConversation = activeConversationId
            ? loadLocalAdminConversations().find((item) => item.id === activeConversationId)
            : null;
          const localConversation =
            currentLocalConversation
              ? {
                  ...currentLocalConversation,
                  updated_at: new Date().toISOString(),
                  mode: chatMode,
                  messages: [...currentLocalConversation.messages, userMessage, assistantMessage],
                }
              : createLocalAdminConversation({
                  title: buildConversationTitle(text),
                  mode: chatMode,
                  messages: [userMessage, assistantMessage],
                });
          const saved = upsertLocalAdminConversation(localConversation);
          setHistoryMode("local");
          setConversations(saved);
          setActiveConversationId(localConversation.id);
        } else if (token) {
          try {
            const assistantPayload =
              extractedVideos.length > 0
                ? { videos: extractedVideos, reply: assistantText, mode: requestMode }
                : { reply: assistantText, mode: requestMode };

            if (activeConversationId) {
              await addConversationMessages(token, activeConversationId, {
                user_message: text,
                assistant_message: assistantText,
                assistant_payload: assistantPayload,
              });
            } else {
              const created = await createConversation(token, {
                title: buildConversationTitle(text),
                user_message: text,
                assistant_message: assistantText,
                assistant_payload: assistantPayload,
              });
              setActiveConversationId(created.id);
              setConversations((prev) => [created, ...prev]);
            }
          } catch (persistErr) {
            const localConversation = createLocalAdminConversation({
              title: buildConversationTitle(text),
              mode: chatMode,
              messages: [userMessage, assistantMessage],
            });
            const saved = upsertLocalAdminConversation(localConversation);
            setHistoryMode("local");
            setConversations(saved);
            setActiveConversationId(localConversation.id);
            setHistoryError(
              isUserNotFoundError(persistErr)
                ? "The chat worked, but this admin account is not in the AR database, so history switched to local mode."
                : "The chat worked, but remote history was unavailable, so history switched to local mode.",
            );
          }
        }
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "The assistant is unavailable right now.";
        setError(message);
        setMessages((current) => [
          ...current,
          {
            id: `a-error-${Date.now()}`,
            role: "assistant",
            content: "Sorry, I could not reach the assistant service right now. Please try again.",
          },
        ]);
      } finally {
        setIsSending(false);
      }
    },
    [activeConversationId, chatMode, fetchToken, historyMode, input, isSending, messages, userId],
  );

  const currentConversationLabel = useMemo(() => {
    if (!activeConversationId) return "New test conversation";
    const current = conversations.find((item) => item.id === activeConversationId);
    return current ? formatConversationLabel(current) : "Saved conversation";
  }, [activeConversationId, conversations]);

  if (!isLoaded || !isSignedIn) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
        <CircularProgress size={28} sx={{ color: "#4D8AFF" }} />
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", lg: "320px minmax(0, 1fr)" },
        gap: 2,
      }}
    >
      <Card
        variant="outlined"
        sx={{
          borderRadius: 3,
          borderColor: "#e5e7eb",
          bgcolor: "#fff",
        }}
      >
        <CardContent sx={{ p: 0 }}>
          <Box
            sx={{
              px: 2.5,
              py: 2,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <Box>
              <Typography fontSize={16} fontWeight={700}>
                Saved Tests
              </Typography>
              <Typography fontSize={12} color="text.secondary">
                Your admin-side chatbot sessions
              </Typography>
            </Box>
            <Button
              size="small"
              variant="outlined"
              startIcon={<Plus style={{ width: 14, height: 14 }} />}
              onClick={startNewConversation}
              sx={{ textTransform: "none", borderRadius: 999 }}
            >
              New
            </Button>
          </Box>
          <Divider />
          {historyError ? (
            <Alert severity="warning" sx={{ m: 2 }}>
              {historyError}
            </Alert>
          ) : null}
          {loadingHistory ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
              <CircularProgress size={22} sx={{ color: "#4D8AFF" }} />
            </Box>
          ) : conversations.length === 0 ? (
            <Box sx={{ px: 2.5, py: 4 }}>
              <Typography fontSize={13} color="text.secondary">
                No saved admin tests yet.
              </Typography>
            </Box>
          ) : (
            <Box sx={{ maxHeight: { lg: 700 }, overflowY: "auto" }}>
              {conversations.map((conversation) => {
                const active = conversation.id === activeConversationId;
                const isLoadingCurrent = loadingConversationId === conversation.id;
                return (
                  <Box
                    key={conversation.id}
                    sx={{
                      px: 2.5,
                      py: 1.75,
                      borderBottom: "1px solid #f1f5f9",
                      bgcolor: active ? "#f8fbff" : "transparent",
                    }}
                  >
                    <Box sx={{ display: "flex", gap: 1, alignItems: "flex-start" }}>
                      <Box
                        onClick={() => loadConversation(conversation.id)}
                        sx={{
                          flex: 1,
                          cursor: "pointer",
                          minWidth: 0,
                        }}
                      >
                        <Typography fontSize={13} fontWeight={700} noWrap>
                          {formatConversationLabel(conversation)}
                        </Typography>
                        <Typography fontSize={11} color="text.secondary" sx={{ mt: 0.5 }}>
                          {new Date(conversation.created_at).toLocaleString()}
                        </Typography>
                      </Box>
                      <Button
                        size="small"
                        color="error"
                        onClick={() => handleDeleteConversation(conversation.id)}
                        sx={{
                          minWidth: 0,
                          p: 0.5,
                          borderRadius: 999,
                        }}
                      >
                        <Trash2 style={{ width: 14, height: 14 }} />
                      </Button>
                    </Box>
                    {isLoadingCurrent ? (
                      <Box sx={{ mt: 1 }}>
                        <CircularProgress size={14} sx={{ color: "#4D8AFF" }} />
                      </Box>
                    ) : null}
                  </Box>
                );
              })}
            </Box>
          )}
        </CardContent>
      </Card>

      <Card
        variant="outlined"
        sx={{
          borderRadius: 3,
          borderColor: "#e5e7eb",
          minHeight: 620,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            px: 2.5,
            py: 2,
            borderBottom: "1px solid #e5e7eb",
            bgcolor: "#f8fafc",
          }}
        >
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={1}
            justifyContent="space-between"
          >
            <Box>
              <Typography fontSize={18} fontWeight={700}>
                {currentConversationLabel}
              </Typography>
              <Typography fontSize={12} color="text.secondary" sx={{ mt: 0.5 }}>
                Use this panel to test chatbot replies as an admin.
              </Typography>
            </Box>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }}>
              <ButtonGroup size="small" variant="outlined" sx={{ bgcolor: "#fff" }}>
                <Button
                  onClick={() => setChatMode("default")}
                  variant={chatMode === "default" ? "contained" : "outlined"}
                  sx={{ textTransform: "none" }}
                >
                  Test Chat
                </Button>
                <Button
                  onClick={() => setChatMode("video_search")}
                  variant={chatMode === "video_search" ? "contained" : "outlined"}
                  sx={{ textTransform: "none" }}
                >
                  Test Search
                </Button>
              </ButtonGroup>
              <Box
                sx={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 1,
                  px: 1.25,
                  py: 0.75,
                  borderRadius: 999,
                  bgcolor: "#fff",
                  border: "1px solid #dbeafe",
                  color: "#1d4ed8",
                  alignSelf: { xs: "flex-start", sm: "center" },
                }}
              >
                <MessageSquare style={{ width: 14, height: 14 }} />
                <Typography fontSize={12} fontWeight={700}>
                  {historyMode === "local" ? "Saved locally for this admin browser" : "Persisted to AR history"}
                </Typography>
              </Box>
            </Stack>
          </Stack>
        </Box>

        <Box
          sx={{
            flex: 1,
            overflowY: "auto",
            px: { xs: 1.5, sm: 2.5 },
            py: 2,
            display: "flex",
            flexDirection: "column",
            gap: 1.25,
            bgcolor: "#fcfcfd",
          }}
        >
          {messages.map((message) => {
            const isUser = message.role === "user";
            return (
              <Box
                key={message.id}
                sx={{
                  alignSelf: isUser ? "flex-end" : "flex-start",
                  width: "min(100%, 760px)",
                  maxWidth: "92%",
                }}
              >
                <Box
                  sx={{
                    px: 1.5,
                    py: 1.25,
                    borderRadius: 3,
                    bgcolor: isUser ? "#111827" : "#fff",
                    color: isUser ? "#fff" : "#111827",
                    border: isUser ? "none" : "1px solid #e5e7eb",
                    boxShadow: isUser
                      ? "0 16px 36px rgba(17,24,39,0.18)"
                      : "0 12px 30px rgba(15,23,42,0.06)",
                  }}
                >
                  <Typography fontSize={14} sx={{ whiteSpace: "pre-wrap" }}>
                    {message.content}
                  </Typography>
                  {!isUser && Array.isArray(message.videos) && message.videos.length > 0 ? (
                    <Box
                      sx={{
                        mt: 1.25,
                        display: "grid",
                        gridTemplateColumns: {
                          xs: "1fr",
                          md: "repeat(2, minmax(0, 1fr))",
                        },
                        gap: 1,
                      }}
                    >
                      {message.videos.map((video) => (
                        <Box
                          key={video.video_id}
                          component="a"
                          href={buildVideoDetailsUrl(video.video_id)}
                          target="_blank"
                          rel="noreferrer"
                          sx={{
                            display: "flex",
                            gap: 1,
                            textDecoration: "none",
                            color: "inherit",
                            p: 1,
                            borderRadius: 2,
                            border: "1px solid #e5e7eb",
                            bgcolor: "#f8fafc",
                            "&:hover": { borderColor: "#93c5fd", bgcolor: "#eff6ff" },
                          }}
                        >
                          <Box
                            component="img"
                            src={video.thumbnail || "/placeholder.jpg"}
                            alt={video.title || video.video_id}
                            sx={{
                              width: 88,
                              height: 56,
                              objectFit: "cover",
                              borderRadius: 1.5,
                              bgcolor: "#e5e7eb",
                              flexShrink: 0,
                            }}
                          />
                          <Box sx={{ minWidth: 0 }}>
                            <Typography fontSize={12} fontWeight={700} noWrap>
                              {video.title || "Untitled video"}
                            </Typography>
                            <Typography fontSize={11} color="text.secondary" noWrap>
                              {video.video_id}
                            </Typography>
                          </Box>
                        </Box>
                      ))}
                    </Box>
                  ) : null}
                </Box>
              </Box>
            );
          })}

          {isSending ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <CircularProgress size={16} sx={{ color: "#4D8AFF" }} />
              <Typography fontSize={12} color="text.secondary">
                Waiting for the assistant...
              </Typography>
            </Box>
          ) : null}

          <div ref={bottomRef} />
        </Box>

        <Box sx={{ borderTop: "1px solid #e5e7eb", p: 2 }}>
          {error ? (
            <Alert severity="error" sx={{ mb: 1.5 }}>
              {error}
            </Alert>
          ) : null}
          <Box component="form" onSubmit={handleSubmit} sx={{ display: "flex", gap: 1 }}>
            <TextField
              fullWidth
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={
                chatMode === "video_search"
                  ? "Search for videos as an admin..."
                  : "Ask the chatbot something as an admin..."
              }
              disabled={isSending}
              multiline
              minRows={2}
              maxRows={6}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={isSending || !input.trim()}
              startIcon={isSending ? <CircularProgress size={14} color="inherit" /> : <Send style={{ width: 14, height: 14 }} />}
              sx={{
                alignSelf: "stretch",
                px: 2,
                minWidth: 132,
                textTransform: "none",
                borderRadius: 2,
                bgcolor: "#111827",
                "&:hover": { bgcolor: "#1f2937" },
              }}
            >
              {isSending ? "Sending..." : "Send"}
            </Button>
          </Box>
        </Box>
      </Card>
    </Box>
  );
}
