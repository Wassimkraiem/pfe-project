"use client";

import { Suspense, useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { z } from "zod";
import { Plus, Globe, X, AlertCircle, Info } from "lucide-react";
import StepIndicator from "@/components/StepIndicator";
import { useBeforeUnload } from "@/hooks/useBeforeUnload";
import { addChannelsToSession, removeChannelFromSession, getOnboardingSessionByEmail } from "@/lib/api";
import { normalizeToHttps, sanitizeChannelUrl, normalizeChannelUrlForCompare } from "@/lib/channelUrl";
import { Box, Typography, TextField, Button, IconButton, CircularProgress } from "@mui/material";

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
        const hostname = u.hostname.replace(/^\[.*\]$/, ""); // strip IPv6 brackets
        return hostname.includes(".");
      } catch {
        return false;
      }
    },
    { message: "Please enter a valid URL with a domain (e.g. https://example.com or https://instagram.com/yourhandle)" }
  )
  .transform((val) => sanitizeChannelUrl(normalizeToHttps(val)));

const STEP_LABELS = {
  email: "Email",
  pages: "Pages",
  checkout: "Checkout",
  reviewSubmit: "Review & Submit",
  account: "Account",
} as const;

const PRICE_PER_CHANNEL = 399;

interface Channel {
  id: string;
  url: string;
  type: string;
  requiresCustomQuote?: boolean;
}

function PagesStepContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const email = searchParams.get("email") ?? "";

  const [url, setUrl] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [addLoading, setAddLoading] = useState(false);
  const [removingChannelId, setRemovingChannelId] = useState<string | null>(null);
  const [continueError, setContinueError] = useState<string | null>(null);
  const [channelsLoading, setChannelsLoading] = useState(true);
  const [channelsDataReceived, setChannelsDataReceived] = useState(false);
  const [hasCustomQuoteTriggers, setHasCustomQuoteTriggers] = useState(false);
  const [customQuoteTriggerUrls, setCustomQuoteTriggerUrls] = useState<string[]>([]);
  const [isPagesLocked, setIsPagesLocked] = useState(false);
  const [lockedPriceId, setLockedPriceId] = useState<string | null>(null);
  const [customQuoteSubmitted, setCustomQuoteSubmitted] = useState(false);
  const currentStep = 2;

  useBeforeUnload(true);

  useEffect(() => {
    if (!email.trim()) {
      router.replace("/signup");
    }
  }, [email, router]);

  type SessionData = {
    requires_custom_quote?: boolean;
    custom_quote_submitted?: boolean;
    custom_quote_triggers?: { channel_url?: string; flag?: string; message?: string }[];
    price_id?: string | number | null;
    pages?: {
      channels?: (string | { url?: string })[];
      custom_quote_triggers?: { channel_url?: string; flag?: string; message?: string }[];
    };
    session_details?: {
      price_id?: string | number | null;
      pages?: {
        channels?: (string | { url?: string; requires_custom_quote?: boolean })[];
        custom_quote_triggers?: { channel_url?: string; flag?: string; message?: string }[];
      };
      custom_quote_triggers?: { channel_url?: string; flag?: string; message?: string }[];
    };
  };

  const getSessionPriceId = (data: SessionData | null) => {
    const direct = data?.price_id;
    if (direct !== null && direct !== undefined) {
      const asString = String(direct).trim();
      if (asString) return asString;
    }
    const nested = data?.session_details?.price_id;
    if (nested !== null && nested !== undefined) {
      const asString = String(nested).trim();
      if (asString) return asString;
    }
    return null;
  };

  const applySessionToState = useCallback((data: SessionData | null) => {
    const priceId = getSessionPriceId(data);
    setIsPagesLocked(!!priceId);
    setLockedPriceId(priceId);
    setCustomQuoteSubmitted(Boolean(data?.custom_quote_submitted));
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
    if (isPagesLocked) return;
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

  const handleRemoveChannel = async (id: string) => {
    if (isPagesLocked) return;
    const channelToRemove = channels.find((channel) => channel.id === id);
    if (!channelToRemove || removingChannelId != null) return;
    setRemovingChannelId(id);
    try {
      await removeChannelFromSession(email, channelToRemove.url);
      refreshChannelsFromSession();
    } catch (err) {
      setContinueError(
        err instanceof Error ? err.message : "Failed to remove channel. Please try again."
      );
      setTimeout(() => setContinueError(null), 5000);
    } finally {
      setRemovingChannelId(null);
    }
  };

  const total = channels.length * PRICE_PER_CHANNEL;
  const channelInTriggers = (c: Channel) =>
    customQuoteTriggerUrls.includes(normalizeChannelUrlForCompare(c.url));
  const sessionRequiresQuote = channels.some(channelInTriggers);
  const customQuoteRequired = hasCustomQuoteTriggers && sessionRequiresQuote;
  const shouldSkipReview = Boolean(lockedPriceId && customQuoteSubmitted);
  const effectiveCustomQuoteRequired = customQuoteRequired && !shouldSkipReview;
  const steps = [
    { number: 1, label: STEP_LABELS.email },
    { number: 2, label: STEP_LABELS.pages },
    { number: 3, label: effectiveCustomQuoteRequired ? STEP_LABELS.reviewSubmit : STEP_LABELS.checkout },
    { number: 4, label: STEP_LABELS.account },
  ];

  const handleContinueToPayment = (e: React.MouseEvent) => {
    e.preventDefault();
    if (channels.length === 0) return;
    setContinueError(null);
    router.push(
      `/signup/checkout?email=${encodeURIComponent(email)}&channels=${channels.length}${
        lockedPriceId ? `&price_id=${encodeURIComponent(lockedPriceId)}` : ""
      }`
    );
  };

  const handleReviewAndSubmit = (e: React.MouseEvent) => {
    e.preventDefault();
    if (channels.length === 0) return;
    setContinueError(null);
    router.push(`/signup/review?email=${encodeURIComponent(email)}`);
  };

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
          <StepIndicator
            steps={steps}
            currentStep={currentStep}
          />
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
              {isPagesLocked ? "Review Your Subscription Details" : "Build Your Subscription"}
            </Typography>
            {!isPagesLocked && (
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
            )}
          </Box>

          {!isPagesLocked && (
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
                  alignItems: { xs: "stretch", sm: "flex-start" },
                  gap: 1.5,
                }}
              >
                <TextField
                  type="url"
                  placeholder="https://instagram.com/yourhandle"
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    if (urlError) setUrlError(null);
                  }}
                  onKeyDown={(e) => e.key === "Enter" && handleAddChannel()}
                  error={!!urlError}
                  fullWidth
                  size="small"
                  required
                  sx={{
                    flex: 1,
                    minWidth: 0,
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
                    minHeight: 44,
                    width: { xs: "100%", sm: "auto" },
                    flexShrink: 0,
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
              {urlError && (
                <Typography variant="caption" color="error" sx={{ display: "block", mt: 1 }}>
                  {urlError}
                </Typography>
              )}
            </Box>
          )}

          {/* Channels: loader until data received, then list or empty state */}
          {!channelsDataReceived && (
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
          )}
          {channelsDataReceived && channels.length === 0 && (
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
          )}
          {channelsDataReceived && channels.length > 0 && (
            <Box sx={{ mt: { xs: 3, sm: 4 } }}>
              <Typography fontWeight={600}>
                Your Channels
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
                    {!(isPagesLocked && channelInTriggers(channel)) && (
                      <IconButton
                        onClick={() => handleRemoveChannel(channel.id)}
                        disabled={removingChannelId != null || isPagesLocked}
                        size="small"
                        sx={{
                          ml: 1,
                          color: "#9ca3af",
                          "&:hover": { color: "#111827" },
                        }}
                        aria-label="Remove channel"
                      >
                        {removingChannelId === channel.id ? (
                          <CircularProgress size={20} sx={{ color: "#9ca3af" }} />
                        ) : (
                          <X style={{ width: 20, height: 20 }} />
                        )}
                      </IconButton>
                    )}
                  </Box>
                ))}
              </Box>

              {/* When custom quote required: show Custom Quote Required message box, hide total */}
              {effectiveCustomQuoteRequired && (
                <Box
                  sx={{
                    mt: 3,
                    p: 2,
                    borderRadius: 3,
                    border: "1px solid #bae6fd",
                    bgcolor: "rgba(224, 242, 254, 0.6)",
                    display: "flex",
                    gap: 1.5,
                    alignItems: "flex-start",
                  }}
                >
                  <Box
                    sx={{
                      width: 28,
                      height: 28,
                      borderRadius: "50%",
                      bgcolor: "#4D8AFF",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    <Info
                      style={{ width: 16, height: 16, color: "white" }}
                      strokeWidth={2.5}
                    />
                  </Box>
                  <Box>
                    <Typography
                      fontWeight={700}
                      sx={{ color: "#1e40af", fontSize: "0.9375rem" }}
                    >
                      Custom Quote Required
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{
                        mt: 0.5,
                        lineHeight: 1.5,
                        color: "#1e3a8a",
                      }}
                    >
                      One or more of your channels requires a custom quote due to 2M+ followers or
                      manual review. Our team will evaluate all your channels and send you
                      personalized pricing within 24–48 hours.
                    </Typography>
                  </Box>
                </Box>
              )}

              {/* Subscription Total – hidden when custom quote required */}
              {!effectiveCustomQuoteRequired && !(lockedPriceId && customQuoteSubmitted) && (
              <Box
                sx={{
                  mt: 3,
                  p: 2,
                  borderRadius: 3,
                  border: "1px solid #e5e7eb",
                  display: "flex",
                  flexDirection: { xs: "column", sm: "row" },
                  alignItems: { sm: "center" },
                  justifyContent: "space-between",
                  gap: 1,
                }}
              >
                <Box>
                  <Typography fontWeight={600} fontSize="0.875rem">
                    Subscription Total
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {channels.length} channel{channels.length !== 1 ? "s" : ""}{" "}
                    × ${PRICE_PER_CHANNEL}/month
                  </Typography>
                </Box>
                <Box sx={{ textAlign: { sm: "right" } }}>
                  <Typography
                    variant="h5"
                    fontWeight="bold"
                    sx={{ fontSize: { xs: "1.5rem", sm: "1.875rem" } }}
                  >
                    ${total}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    /month
                  </Typography>
                </Box>
              </Box>
              )}
            </Box>
          )}

          {/* Navigation Buttons */}
          {continueError && (
            <Typography color="error" fontSize="0.875rem" sx={{ mt: 2, textAlign: "center" }}>
              {continueError}
            </Typography>
          )}
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
              href="/signup"
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
              onClick={effectiveCustomQuoteRequired ? handleReviewAndSubmit : handleContinueToPayment}
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
              {effectiveCustomQuoteRequired ? "Review & Submit" : "Continue to Payment"}
            </Button>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

export default function PagesStep() {
  return (
    <Suspense
      fallback={
        <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "#fafafa" }}>
          <CircularProgress />
        </Box>
      }
    >
      <PagesStepContent />
    </Suspense>
  );
}
