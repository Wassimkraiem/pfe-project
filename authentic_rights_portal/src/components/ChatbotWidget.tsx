"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import ChatRoundedIcon from "@mui/icons-material/ChatRounded";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import SendRoundedIcon from "@mui/icons-material/SendRounded";
import AddRoundedIcon from "@mui/icons-material/AddRounded";
import HistoryRoundedIcon from "@mui/icons-material/HistoryRounded";
import ArrowBackRoundedIcon from "@mui/icons-material/ArrowBackRounded";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import MicRoundedIcon from "@mui/icons-material/MicRounded";
import StopRoundedIcon from "@mui/icons-material/StopRounded";
import {
  Box,
  CircularProgress,
  Fab,
  IconButton,
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

const CHAT_PROXY_URL = "/api/chat";
const TRANSCRIBE_PROXY_URL = "/api/transcribe";
const VIDEOSEARCH_PORTAL_BASE_URL =
  process.env.NEXT_PUBLIC_VIDEOSEARCH_PORTAL_URL?.replace(/\/$/, "") ||
  "http://localhost:3002";

const WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "Hi, I am your BVIRAL assistant. Ask me about onboarding, plans, licensing, or support.",
};

function buildVideoDetailsUrl(videoId: string): string {
  return `${VIDEOSEARCH_PORTAL_BASE_URL}/video/${encodeURIComponent(videoId)}`;
}

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

function extractVideos(payload: unknown): VideoResult[] {
  if (!payload || typeof payload !== "object") return [];
  const r = payload as Record<string, unknown>;
  const videos = r.videos ?? (r.data as Record<string, unknown> | undefined)?.videos;
  if (!Array.isArray(videos)) return [];
  return videos.filter(
    (item): item is VideoResult =>
      !!item && typeof item === "object" && typeof (item as VideoResult).video_id === "string",
  );
}

function extractVideosFromMessagePayload(payload: unknown): VideoResult[] {
  if (!payload || typeof payload !== "object") return [];
  const maybeVideos = (payload as { videos?: unknown }).videos;
  if (!Array.isArray(maybeVideos)) return [];
  return maybeVideos.filter(
    (item): item is VideoResult =>
      !!item && typeof item === "object" && typeof (item as VideoResult).video_id === "string",
  );
}

function extractReplyFromMessagePayload(payload: unknown): string {
  if (!payload || typeof payload !== "object") return "";
  const maybeReply = (payload as { reply?: unknown }).reply;
  return typeof maybeReply === "string" ? maybeReply : "";
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
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [recordingError, setRecordingError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const historyLoadedRef = useRef(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

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
          content:
            m.role === "assistant"
              ? m.content || extractReplyFromMessagePayload(m.payload)
              : m.content,
          videos:
            m.role === "assistant"
              ? extractVideosFromMessagePayload(m.payload)
              : undefined,
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
          mode: "video_search",
          input_message: text,
          message: text,
          user_id: userId ?? "web-anonymous",
          history: nextMessages.map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      if (!response.ok) throw new Error(`Chat API returned ${response.status}`);

      const payload = (await response.json()) as unknown;
      const extractedAssistantText = extractAssistantReply(payload);
      const extractedVideos = extractVideos(payload);
      const assistantText =
        extractedAssistantText === "I could not read a response from the assistant." &&
        extractedVideos.length > 0
          ? `Found ${extractedVideos.length} videos for your request.`
          : extractedAssistantText;
      const assistantMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: assistantText,
        videos: extractedVideos.length > 0 ? extractedVideos : undefined,
      };
      setMessages((cur) => [...cur, assistantMsg]);

      if (isSignedIn) {
        const token = await fetchToken();
        if (token) {
          try {
            const assistantPayload =
              extractedVideos.length > 0
                ? { videos: extractedVideos, reply: assistantText }
                : undefined;
            if (activeConversationId) {
              await addConversationMessages(token, activeConversationId, {
                user_message: text,
                assistant_message: assistantText,
                assistant_payload: assistantPayload,
              });
            } else {
              const created = await createConversation(token, {
                user_message: text,
                assistant_message: assistantText,
                assistant_payload: assistantPayload,
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

  const stopRecording = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
  }, []);

  const startRecording = useCallback(async () => {
    setRecordingError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setRecordingError("Voice input is not supported in this browser.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const mimeType =
        typeof MediaRecorder !== "undefined" &&
        MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "";
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        setIsRecording(false);
        const audioBlob = new Blob(chunksRef.current, { type: "audio/webm" });
        chunksRef.current = [];
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;

        if (!audioBlob.size) return;
        setIsTranscribing(true);
        try {
          const formData = new FormData();
          formData.append("audio", audioBlob, "recording.webm");
          const response = await fetch(TRANSCRIBE_PROXY_URL, {
            method: "POST",
            body: formData,
          });
          if (!response.ok) throw new Error(`Transcription failed (${response.status})`);
          const payload = (await response.json()) as { text?: string };
          const transcript = (payload.text ?? "").trim();
          if (transcript) {
            setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
          }
        } catch {
          setRecordingError("Could not transcribe audio. Please try again.");
        } finally {
          setIsTranscribing(false);
        }
      };

      recorder.start();
      setIsRecording(true);
    } catch {
      setRecordingError("Microphone access was denied.");
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      if (recorderRef.current && recorderRef.current.state !== "inactive") {
        recorderRef.current.stop();
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  if (!isLoaded || !isSignedIn) return null;

  return (
    <>
      {isOpen ? (
        <Box
          sx={{
            position: "fixed",
            top: 0,
            right: 0,
            bottom: 0,
            width: { xs: "100vw", sm: 560 },
            zIndex: 1400,
            display: "flex",
            flexDirection: "column",
            boxShadow: "-4px 0 24px rgba(17,24,39,0.12)",
            background:
              "linear-gradient(180deg, rgba(255,255,255,0.99) 0%, rgba(248,250,252,0.99) 100%)",
            borderLeft: "1px solid",
            borderColor: "divider",
          }}
        >
          {/* Header */}
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ px: 2.5, py: 2, borderBottom: "1px solid", borderColor: "divider", flexShrink: 0 }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              {showHistory && (
                <IconButton size="small" onClick={() => setShowHistory(false)}>
                  <ArrowBackRoundedIcon fontSize="small" />
                </IconButton>
              )}
              <Box>
                <Typography variant="h6" fontWeight={700} fontSize="1rem">
                  {showHistory ? "Conversations" : "BVIRAL Assistant"}
                </Typography>
                {!showHistory && (
                  <Typography variant="body2" color="text.secondary">
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
            <Box sx={{ flex: 1, overflowY: "auto" }}>
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
                  flex: 1,
                  overflowY: "auto",
                  px: 2,
                  py: 2,
                  display: "flex",
                  flexDirection: "column",
                  gap: 1.5,
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
                          maxWidth: "85%",
                          borderRadius: 2.5,
                          px: 2,
                          py: 1.25,
                          bgcolor: isUser ? "primary.main" : "grey.100",
                          color: isUser ? "primary.contrastText" : "text.primary",
                          boxShadow: isUser
                            ? "0 8px 18px rgba(77, 138, 255, 0.28)"
                            : "0 4px 10px rgba(17,24,39,0.08)",
                        }}
                      >
                        <Typography variant="body1" sx={{ whiteSpace: "pre-wrap", fontSize: "0.925rem" }}>
                          {message.content}
                        </Typography>
                        {message.role === "assistant" &&
                          Array.isArray(message.videos) &&
                          message.videos.length > 0 && (
                            <Box sx={{ mt: 1, display: "grid", gap: 0.75 }}>
                              <Typography
                                variant="caption"
                                sx={{ display: "block", opacity: 0.9 }}
                              >
                                {message.videos.length} video result
                                {message.videos.length > 1 ? "s" : ""}
                              </Typography>
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
                                    alignItems: "center",
                                    p: 0.75,
                                    borderRadius: 1.5,
                                    textDecoration: "none",
                                    color: "inherit",
                                    bgcolor: "rgba(255,255,255,0.55)",
                                    border: "1px solid rgba(17,24,39,0.08)",
                                    "&:hover": { bgcolor: "rgba(255,255,255,0.8)" },
                                  }}
                                >
                                  <Box
                                    component="img"
                                    src={video.thumbnail || "/placeholder.jpg"}
                                    alt={video.title || video.video_id}
                                    sx={{
                                      width: 80,
                                      height: 52,
                                      borderRadius: 1,
                                      objectFit: "cover",
                                      flexShrink: 0,
                                      bgcolor: "grey.200",
                                    }}
                                  />
                                  <Box sx={{ minWidth: 0 }}>
                                    <Typography variant="caption" fontWeight={700} noWrap>
                                      {video.title || "Untitled video"}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary" noWrap>
                                      {video.video_id}
                                    </Typography>
                                  </Box>
                                </Box>
                              ))}
                            </Box>
                          )}
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
                  p: 2,
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
                  placeholder={isRecording ? "Listening..." : "Ask a question..."}
                  disabled={isSending || isTranscribing}
                />
                <IconButton
                  type="button"
                  color={isRecording ? "error" : "default"}
                  disabled={isSending || isTranscribing}
                  onClick={isRecording ? stopRecording : startRecording}
                  title={isRecording ? "Stop recording" : "Start voice input"}
                  sx={{
                    borderRadius: 1.5,
                    border: "1px solid",
                    borderColor: isRecording ? "error.main" : "divider",
                  }}
                >
                  {isRecording ? (
                    <StopRoundedIcon fontSize="small" />
                  ) : (
                    <MicRoundedIcon fontSize="small" />
                  )}
                </IconButton>
                <IconButton
                  type="submit"
                  color="primary"
                  disabled={isSending || isTranscribing || !input.trim()}
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
              {(isRecording || isTranscribing || recordingError) && (
                <Box sx={{ px: 1.25, pb: 1 }}>
                  <Typography variant="caption" color={recordingError ? "error" : "text.secondary"}>
                    {recordingError
                      ? recordingError
                      : isTranscribing
                        ? "Transcribing audio..."
                        : "Recording... click stop when done."}
                  </Typography>
                </Box>
              )}
            </>
          )}
        </Box>
      ) : (
        <Box
          sx={{
            position: "fixed",
            right: { xs: 12, sm: 20 },
            bottom: { xs: 12, sm: 20 },
            zIndex: 1400,
          }}
        >
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
        </Box>
      )}
    </>
  );
}
