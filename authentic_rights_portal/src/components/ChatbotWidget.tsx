"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import ChatRoundedIcon from "@mui/icons-material/ChatRounded";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import SendRoundedIcon from "@mui/icons-material/SendRounded";
import AddRoundedIcon from "@mui/icons-material/AddRounded";
import HistoryRoundedIcon from "@mui/icons-material/HistoryRounded";
import ArrowBackRoundedIcon from "@mui/icons-material/ArrowBackRounded";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import {
  Box,
  CircularProgress,
  Fab,
  IconButton,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useAuth } from "@clerk/nextjs";
import { getApiToken } from "@/lib/auth";
import {
  addConversationMessages,
  ConversationSummary,
  createConversation,
  deleteConversation,
  getConversation,
  getConversations,
} from "@/lib/api";

type ChatRole = "user" | "assistant";

type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
};

const CHAT_PROXY_URL = "/api/chat";
const WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "Hi, I am your BVIRAL assistant. Ask me about onboarding, plans, licensing, or support.",
};

function extractAssistantReply(payload: unknown): string {
  if (typeof payload === "string") return payload;
  if (!payload || typeof payload !== "object")
    return "I could not read a response from the assistant.";

  const r = payload as Record<string, unknown>;
  const d = (r.data ?? {}) as Record<string, unknown>;
  return (
    (r.answer as string) ??
    (r.reply as string) ??
    (r.response as string) ??
    (r.message as string) ??
    (d.answer as string) ??
    (d.reply as string) ??
    (d.response as string) ??
    (d.message as string) ??
    "I could not read a response from the assistant."
  );
}

export default function ChatbotWidget() {
  const { isLoaded, userId, getToken } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const historyLoadedRef = useRef(false);

  const isSignedIn = !!userId;

  const scrollToBottom = useCallback(() => {
    const t = setTimeout(() => {
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }, 50);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (isOpen) scrollToBottom();
  }, [isOpen, messages, isSending, scrollToBottom]);

  const fetchToken = useCallback(async (): Promise<string | null> => {
    if (!isSignedIn) return null;
    return getApiToken(getToken);
  }, [isSignedIn, getToken]);

  const loadConversations = useCallback(async () => {
    const token = await fetchToken();
    if (!token) return;
    try {
      const list = await getConversations(token);
      setConversations(list);
      return list;
    } catch {
      /* silent */
    }
  }, [fetchToken]);

  const loadConversation = useCallback(
    async (id: number) => {
      const token = await fetchToken();
      if (!token) return;
      setIsLoadingHistory(true);
      try {
        const detail = await getConversation(token, id);
        const loaded: ChatMessage[] = detail.messages.map((m) => ({
          id: `db-${m.id}`,
          role: m.role,
          content: m.content,
        }));
        setMessages(loaded.length > 0 ? loaded : [WELCOME_MESSAGE]);
        setActiveConversationId(id);
        setShowHistory(false);
      } catch {
        /* silent */
      } finally {
        setIsLoadingHistory(false);
      }
    },
    [fetchToken],
  );

  useEffect(() => {
    if (!isOpen || !isSignedIn || historyLoadedRef.current) return;
    historyLoadedRef.current = true;
    (async () => {
      const list = await loadConversations();
      if (list && list.length > 0) {
        await loadConversation(list[0].id);
      }
    })();
  }, [isOpen, isSignedIn, loadConversations, loadConversation]);

  const startNewChat = () => {
    setActiveConversationId(null);
    setMessages([WELCOME_MESSAGE]);
    setShowHistory(false);
  };

  const handleDeleteConversation = async (id: number) => {
    const token = await fetchToken();
    if (!token) return;
    try {
      await deleteConversation(token, id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversationId === id) startNewChat();
    } catch {
      /* silent */
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const text = input.trim();
    if (!text || isSending) return;

    const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: "user", content: text };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput("");
    setIsSending(true);

    try {
      const response = await fetch(CHAT_PROXY_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input_message: text,
          message: text,
          user_id: userId ?? "web-anonymous",
          history: nextMessages.map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      if (!response.ok) throw new Error(`Chat API returned ${response.status}`);

      const payload = (await response.json()) as unknown;
      const assistantText = extractAssistantReply(payload);
      const assistantMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: assistantText,
      };
      setMessages((cur) => [...cur, assistantMsg]);

      if (isSignedIn) {
        const token = await fetchToken();
        if (token) {
          try {
            if (activeConversationId) {
              await addConversationMessages(token, activeConversationId, {
                user_message: text,
                assistant_message: assistantText,
              });
            } else {
              const created = await createConversation(token, {
                user_message: text,
                assistant_message: assistantText,
              });
              setActiveConversationId(created.id);
              setConversations((prev) => [created, ...prev]);
            }
          } catch {
            /* persistence failure is non-blocking */
          }
        }
      }
    } catch {
      setMessages((cur) => [
        ...cur,
        {
          id: `a-error-${Date.now()}`,
          role: "assistant",
          content: "Sorry, I could not reach the assistant service right now. Please try again.",
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  if (!isLoaded || !isSignedIn) return null;

  return (
    <Box
      sx={{
        position: "fixed",
        right: { xs: 12, sm: 20 },
        bottom: { xs: 12, sm: 20 },
        zIndex: 1400,
      }}
    >
      {isOpen ? (
        <Paper
          elevation={12}
          sx={{
            width: { xs: "calc(100vw - 24px)", sm: 380 },
            maxWidth: 380,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            overflow: "hidden",
            background:
              "linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,0.98) 100%)",
            backdropFilter: "blur(8px)",
          }}
        >
          {/* Header */}
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ px: 2, py: 1.25, borderBottom: "1px solid", borderColor: "divider" }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              {showHistory && (
                <IconButton size="small" onClick={() => setShowHistory(false)}>
                  <ArrowBackRoundedIcon fontSize="small" />
                </IconButton>
              )}
              <Box>
                <Typography variant="subtitle2" fontWeight={700}>
                  {showHistory ? "Conversations" : "BVIRAL Assistant"}
                </Typography>
                {!showHistory && (
                  <Typography variant="caption" color="text.secondary">
                    Connected to chat support
                  </Typography>
                )}
              </Box>
            </Box>
            <Stack direction="row" spacing={0.25}>
              {isSignedIn && !showHistory && (
                <>
                  <IconButton
                    size="small"
                    onClick={() => {
                      loadConversations();
                      setShowHistory(true);
                    }}
                    title="History"
                  >
                    <HistoryRoundedIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={startNewChat} title="New chat">
                    <AddRoundedIcon fontSize="small" />
                  </IconButton>
                </>
              )}
              <IconButton size="small" onClick={() => setIsOpen(false)}>
                <CloseRoundedIcon fontSize="small" />
              </IconButton>
            </Stack>
          </Stack>

          {/* Body */}
          {showHistory ? (
            <Box sx={{ height: 360, overflowY: "auto" }}>
              {conversations.length === 0 ? (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ textAlign: "center", mt: 4 }}
                >
                  No past conversations
                </Typography>
              ) : (
                conversations.map((conv) => (
                  <Stack
                    key={conv.id}
                    direction="row"
                    alignItems="center"
                    sx={{
                      px: 2,
                      py: 1.25,
                      cursor: "pointer",
                      borderBottom: "1px solid",
                      borderColor: "divider",
                      bgcolor:
                        conv.id === activeConversationId
                          ? "action.selected"
                          : "transparent",
                      "&:hover": { bgcolor: "action.hover" },
                    }}
                    onClick={() => loadConversation(conv.id)}
                  >
                    <Box sx={{ flex: 1, overflow: "hidden" }}>
                      <Typography
                        variant="body2"
                        fontWeight={600}
                        noWrap
                      >
                        {conv.title || "Untitled conversation"}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(conv.created_at).toLocaleDateString()}
                      </Typography>
                    </Box>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteConversation(conv.id);
                      }}
                      title="Delete"
                    >
                      <DeleteOutlineRoundedIcon fontSize="small" />
                    </IconButton>
                  </Stack>
                ))
              )}
            </Box>
          ) : (
            <>
              <Box
                sx={{
                  height: 360,
                  overflowY: "auto",
                  px: 1.5,
                  py: 1.5,
                  display: "flex",
                  flexDirection: "column",
                  gap: 1,
                }}
              >
                {isLoadingHistory ? (
                  <Stack alignItems="center" justifyContent="center" sx={{ flex: 1 }}>
                    <CircularProgress size={24} />
                  </Stack>
                ) : (
                  messages.map((message) => {
                    const isUser = message.role === "user";
                    return (
                      <Box
                        key={message.id}
                        sx={{
                          alignSelf: isUser ? "flex-end" : "flex-start",
                          maxWidth: "88%",
                          borderRadius: 2,
                          px: 1.5,
                          py: 1,
                          bgcolor: isUser ? "primary.main" : "grey.100",
                          color: isUser ? "primary.contrastText" : "text.primary",
                          boxShadow: isUser
                            ? "0 8px 18px rgba(77, 138, 255, 0.28)"
                            : "0 4px 10px rgba(17,24,39,0.08)",
                        }}
                      >
                        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                          {message.content}
                        </Typography>
                      </Box>
                    );
                  })
                )}

                {isSending && (
                  <Stack
                    direction="row"
                    spacing={1}
                    alignItems="center"
                    sx={{ alignSelf: "flex-start", px: 1.5, py: 1 }}
                  >
                    <CircularProgress size={14} />
                    <Typography variant="caption" color="text.secondary">
                      Thinking...
                    </Typography>
                  </Stack>
                )}

                <div ref={bottomRef} />
              </Box>

              <Box
                component="form"
                onSubmit={handleSubmit}
                sx={{
                  display: "flex",
                  gap: 1,
                  p: 1.25,
                  borderTop: "1px solid",
                  borderColor: "divider",
                  bgcolor: "background.paper",
                }}
              >
                <TextField
                  size="small"
                  fullWidth
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask a question..."
                  disabled={isSending}
                />
                <IconButton
                  type="submit"
                  color="primary"
                  disabled={isSending || !input.trim()}
                  sx={{
                    borderRadius: 1.5,
                    bgcolor: "primary.main",
                    color: "primary.contrastText",
                    "&:hover": { bgcolor: "primary.dark" },
                    "&.Mui-disabled": { bgcolor: "grey.300", color: "grey.500" },
                  }}
                >
                  <SendRoundedIcon fontSize="small" />
                </IconButton>
              </Box>
            </>
          )}
        </Paper>
      ) : (
        <Fab
          color="primary"
          variant="extended"
          onClick={() => setIsOpen(true)}
          sx={{
            borderRadius: 999,
            px: 2,
            boxShadow: "0 12px 24px rgba(77, 138, 255, 0.35)",
            textTransform: "none",
            fontWeight: 700,
          }}
        >
          <ChatRoundedIcon sx={{ mr: 1 }} fontSize="small" />
          Assistant Chat
        </Fab>
      )}
    </Box>
  );
}
