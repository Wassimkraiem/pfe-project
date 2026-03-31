"use client";

import { Suspense, useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { z } from "zod";
import { Plus, Globe, AlertCircle } from "lucide-react";
import StepIndicator from "@/components/StepIndicator";
import { useBeforeUnload } from "@/hooks/useBeforeUnload";
import {
  addChannelsToSession,
  getOnboardingSessionByEmail,
} from "@/lib/api";
import { normalizeToHttps, sanitizeChannelUrl, normalizeChannelUrlForCompare } from "@/lib/channelUrl";
import { Box, Typography, TextField, Button, CircularProgress } from "@mui/material";

const urlSchema = z
  .string()
  .min(1, "URL is required")
  .transform((val) => val.trim())
  .refine(
    (val) => {
      const httpsUrl = normalizeToHttps(val);
      try {
        const u = new URL(httpsUrl);
        if (!httpsUrl.startsWith("https://")) return false;
        const hostname = u.hostname.replace(/^\[.*\]$/, "");
        return hostname.includes(".");
      } catch {
        return false;
      }
    },
    {
      message:
        "Please enter a valid URL with a domain (e.g. https://example.com or https://instagram.com/yourhandle)",
    }
  )
  .transform((val) => sanitizeChannelUrl(normalizeToHttps(val)));

const steps = [
  { number: 1, label: "Email" },
  { number: 2, label: "Pages" },
  { number: 3, label: "Request Quote" },
];

interface Channel {
  id: string;
  url: string;
  type: string;
  /** When true, channel is 2M+ followers or manual review; show "Requires custom quote" and custom quote UI. */
  requiresCustomQuote?: boolean;
}

function ContactPagesStepContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const email = searchParams.get("email") ?? "";

  const [url, setUrl] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [addLoading, setAddLoading] = useState(false);
  const [continueError, setContinueError] = useState<string | null>(null);
  const [channelsLoading, setChannelsLoading] = useState(true);
  const [channelsDataReceived, setChannelsDataReceived] = useState(false);
  const [hasCustomQuoteTriggers, setHasCustomQuoteTriggers] = useState(false);
  const [customQuoteTriggerUrls, setCustomQuoteTriggerUrls] = useState<string[]>([]);
  const currentStep = 2;

  useBeforeUnload(true);

  useEffect(() => {
    if (!email.trim()) {
      router.replace("/contact");
    }
  }, [email, router]);

  type SessionData = {
    requires_custom_quote?: boolean;
    custom_quote_triggers?: { channel_url?: string; flag?: string; message?: string }[];
    pages?: {
      channels?: (string | { url?: string })[];
      custom_quote_triggers?: { channel_url?: string; flag?: string; message?: string }[];
    };
    session_details?: {
      pages?: {
        channels?: (string | { url?: string; requires_custom_quote?: boolean })[];
        custom_quote_triggers?: { channel_url?: string; flag?: string; message?: string }[];
      };
      custom_quote_triggers?: { channel_url?: string; flag?: string; message?: string }[];
    };
  };

  const applySessionToState = useCallback((data: SessionData | null) => {
    const sessionRequiresQuote = data?.requires_custom_quote === true;
    const triggers =
      data?.pages?.custom_quote_triggers ??
      data?.custom_quote_triggers ??
      (data?.session_details as { custom_quote_triggers?: { channel_url?: string }[] } | undefined)
        ?.custom_quote_triggers ??
      (data?.session_details as { pages?: { custom_quote_triggers?: { channel_url?: string }[] } } | undefined)
        ?.pages?.custom_quote_triggers;
    const triggerList = Array.isArray(triggers) ? triggers : [];
    const triggerUrls = triggerList
      .map((t) => normalizeChannelUrlForCompare(t.channel_url ?? ""))
      .filter(Boolean);
    const hasTriggers = triggerUrls.length !== 0;
    setHasCustomQuoteTriggers(sessionRequiresQuote && hasTriggers);
    setCustomQuoteTriggerUrls(triggerUrls);
    const pagesNode = data?.session_details?.pages ?? data?.pages;
    const rawList = Array.isArray(pagesNode?.channels) ? pagesNode.channels : [];
    if (rawList.length > 0) {
      setChannels(
        rawList.map((item, i) => {
          const url = typeof item === "string" ? item : item?.url ?? "";
          const inTriggers = triggerUrls.includes(normalizeChannelUrlForCompare(url));
          return {
            id: `loaded-${i}-${url}`,
            url,
            type: "Website",
            requiresCustomQuote: inTriggers,
          };
        })
      );
    } else {
      setChannels([]);
    }
  }, []);

  const lastFetchedEmailRef = useRef<string | null>(null);

  // On mount (e.g. navigating to this step): reset so loader shows until data is loaded
  useEffect(() => {
    lastFetchedEmailRef.current = null;
    setChannelsDataReceived(false);
    setChannelsLoading(true);
  }, []);

  const refreshChannelsFromSession = useCallback(() => {
    if (!email.trim()) return;
    getOnboardingSessionByEmail(email)
      .then((res) => applySessionToState(res.data as SessionData | null))
      .catch(() => {});
  }, [email, applySessionToState]);

  useEffect(() => {
    if (!email.trim()) return;
    if (lastFetchedEmailRef.current === email) return;
    lastFetchedEmailRef.current = email;
    setChannelsDataReceived(false);
    setChannelsLoading(true);
    const controller = new AbortController();
    getOnboardingSessionByEmail(email, controller.signal)
      .then((res) => {
        applySessionToState(res.data as SessionData | null);
        setChannelsDataReceived(true);
      })
      .catch((err) => {
        if (err?.name !== "AbortError") setChannels([]);
        setChannelsDataReceived(true);
      })
      .finally(() => setChannelsLoading(false));
    return () => controller.abort();
  }, [email, applySessionToState]);

  const handleAddChannel = async () => {
    if (addLoading) return;
    setUrlError(null);
    const result = urlSchema.safeParse(url.trim());
    if (!result.success) {
      const firstIssue = result.error.issues[0];
      setUrlError(firstIssue?.message ?? "Please enter a valid URL.");
      return;
    }
    const newUrl = result.data;
    setAddLoading(true);
    try {
      await addChannelsToSession(email, [newUrl]);
      setUrl("");
      refreshChannelsFromSession();
    } catch (err) {
      setUrlError(
        err instanceof Error ? err.message : "Something went wrong. Please try again."
      );
    } finally {
      setAddLoading(false);
    }
  };

  const channelInTriggers = (c: Channel) =>
    customQuoteTriggerUrls.includes(normalizeChannelUrlForCompare(c.url));

  if (!email.trim()) {
    return (
      <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "white" }}>
        <CircularProgress size={32} sx={{ color: "#4D8AFF" }} />
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "white" }}>
      <Box
        sx={{
          maxWidth: "56rem",
          mx: "auto",
          px: { xs: 2, sm: 3, lg: 4 },
          py: { xs: 3, sm: 4 },
        }}
      >
        {/* Step Indicator */}
        <Box sx={{ maxWidth: "42rem", mx: "auto" }}>
          <StepIndicator steps={steps} currentStep={currentStep} />
        </Box>

        {/* Divider */}
        <Box
          sx={{
            mx: "auto",
            mt: 3,
            maxWidth: "42rem",
            borderTop: "1px solid #e5e7eb",
          }}
        />

        {/* Main Content */}
        <Box sx={{ mx: "auto", mt: { xs: 4, sm: 6 }, maxWidth: "42rem" }}>
          <Box sx={{ textAlign: "center" }}>
            <Typography
              variant="h4"
              fontWeight="bold"
              sx={{ fontSize: { xs: "1.5rem", sm: "1.875rem", md: "2.25rem" } }}
            >
              Build Your Subscription
            </Typography>
            <Typography
              variant="body1"
              color="text.secondary"
              sx={{
                mt: { xs: 1, sm: 1.5 },
                fontSize: { xs: "0.875rem", sm: "1rem" },
              }}
            >
              Which social channels would you like to include in your plan?
            </Typography>
          </Box>

          {/* Add Channel Card */}
          <Box
            sx={{
              mt: { xs: 3, sm: 5 },
              p: { xs: 2, sm: 3 },
              borderRadius: 3,
              border: "1px solid #e5e7eb",
            }}
          >
            <Typography fontWeight={600} fontSize="0.875rem">
              Social Profile or Website URL
            </Typography>
            <Box
              sx={{
                mt: 1.5,
                display: "flex",
                flexDirection: { xs: "column", sm: "row" },
                alignItems: { sm: "center" },
                gap: 1.5,
              }}
            >
              <TextField
                type="url"
                placeholder="instagram.com/yourhandle"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  if (urlError) setUrlError(null);
                }}
                onKeyDown={(e) => e.key === "Enter" && handleAddChannel()}
                error={!!urlError}
                helperText={urlError}
                fullWidth
                size="small"
                sx={{
                  flex: 1,
                  "& .MuiOutlinedInput-root": {
                    borderRadius: 2,
                    height: 44,
                  },
                }}
              />
              <Button
                onClick={handleAddChannel}
                disabled={addLoading}
                variant="contained"
                startIcon={
                  addLoading ? (
                    <CircularProgress size={16} color="inherit" sx={{ flexShrink: 0 }} />
                  ) : (
                    <Plus style={{ width: 16, height: 16 }} />
                  )
                }
                sx={{
                  height: 44,
                  width: { xs: "100%", sm: "auto" },
                  bgcolor: "#4D8AFF",
                  "&:hover": { bgcolor: "#3D7AEF" },
                  textTransform: "none",
                  fontWeight: 600,
                  borderRadius: "9999px",
                  px: 2.5,
                }}
              >
                {addLoading ? "Adding…" : "Add"}
              </Button>
            </Box>
          </Box>

          {continueError && (
            <Typography color="error" sx={{ mt: 2 }} variant="body2">
              {continueError}
            </Typography>
          )}

          {/* Channels: loader until data received, then list or empty state */}
          {!channelsDataReceived ? (
            <Box
              sx={{
                mt: { xs: 3, sm: 4 },
                minHeight: 140,
                py: 4,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 2,
                border: "1px dashed #e5e7eb",
                borderRadius: 3,
                bgcolor: "rgba(0,0,0,0.02)",
              }}
            >
              <CircularProgress size={40} sx={{ color: "#4D8AFF" }} />
              <Typography variant="body2" color="text.secondary">
                Loading your channels…
              </Typography>
            </Box>
          ) : channels.length === 0 ? (
            <Box
              sx={{
                mt: { xs: 3, sm: 4 },
                py: 3,
                px: 2,
                borderRadius: 3,
                border: "1px solid #e5e7eb",
                bgcolor: "rgba(0,0,0,0.02)",
                textAlign: "center",
              }}
            >
              <Typography variant="body2" color="text.secondary">
                No channels yet. Add a social profile or website URL above.
              </Typography>
            </Box>
          ) : (
            <Box sx={{ mt: { xs: 3, sm: 4 } }}>
              <Typography fontWeight={600}>
                Your Channels{" "}
                <Typography
                  component="span"
                  fontWeight="normal"
                  color="text.secondary"
                >
                  ({channels.length})
                </Typography>
              </Typography>

              <Box
                sx={{
                  mt: 2,
                  display: "flex",
                  flexDirection: "column",
                  gap: 1.5,
                }}
              >
                {channels.map((channel) => (
                  <Box
                    key={channel.id}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      p: { xs: 1.5, sm: 2 },
                      borderRadius: 3,
                      border: "1px solid #e5e7eb",
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1.5,
                        minWidth: 0,
                        flex: 1,
                      }}
                    >
                      <Globe
                        style={{
                          width: 20,
                          height: 20,
                          flexShrink: 0,
                          color: "#9ca3af",
                        }}
                      />
                      <Box sx={{ minWidth: 0, flex: 1 }}>
                        <Typography
                          fontSize="0.875rem"
                          fontWeight={500}
                          sx={{
                            color: "#4D8AFF",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {channel.url}
                        </Typography>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", mt: 0.25 }}>
                          <Typography variant="caption" color="text.secondary">
                            {channel.type}
                          </Typography>
                          {channelInTriggers(channel) && (
                              <Box
                                component="span"
                                sx={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: 0.5,
                                  px: 1,
                                  py: 0.25,
                                  borderRadius: 1,
                                  bgcolor: "rgba(234, 179, 8, 0.15)",
                                  border: "1px solid rgba(234, 179, 8, 0.4)",
                                }}
                              >
                                <AlertCircle
                                  style={{ width: 12, height: 12, color: "#ca8a04", flexShrink: 0 }}
                                />
                                <Typography
                                  component="span"
                                  variant="caption"
                                  sx={{ fontWeight: 600, color: "#a16207", fontSize: "0.7rem" }}
                                >
                                  Requires custom quote
                                </Typography>
                              </Box>
                          )}
                        </Box>
                      </Box>
                    </Box>
                  </Box>
                ))}
              </Box>
            </Box>
          )}

          {/* Navigation Buttons */}
          <Box
            sx={{
              mt: { xs: 3, sm: 4 },
              display: "flex",
              flexDirection: { xs: "column-reverse", sm: "row" },
              gap: { xs: 1.5, sm: 2 },
            }}
          >
            <Button
              component={Link}
              href="/contact"
              fullWidth
              variant="outlined"
              sx={{
                height: 48,
                textTransform: "none",
                fontWeight: 600,
                borderRadius: "9999px",
                borderColor: "#d1d5db",
                color: "#111827",
                "&:hover": { bgcolor: "#f9fafb", borderColor: "#d1d5db" },
              }}
            >
              Back
            </Button>
            <Button
              fullWidth
              variant="contained"
              disabled={channels.length === 0}
              onClick={(e) => {
                e.preventDefault();
                if (channels.length > 0) {
                  setContinueError(null);
                  router.push(`/contact/quote?email=${encodeURIComponent(email)}`);
                }
              }}
              sx={{
                height: 48,
                bgcolor: "#4D8AFF",
                "&:hover": { bgcolor: "#3D7AEF" },
                "&:disabled": {
                  bgcolor: "rgba(77, 138, 255, 0.5)",
                  color: "white",
                },
                textTransform: "none",
                fontWeight: 600,
                borderRadius: "9999px",
              }}
            >
              Continue to Review
            </Button>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

export default function ContactPagesStep() {
  return (
    <Suspense
      fallback={
        <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "#fafafa" }}>
          <CircularProgress />
        </Box>
      }
    >
      <ContactPagesStepContent />
    </Suspense>
  );
}
