"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Globe, CheckCircle2 } from "lucide-react";
import StepIndicator from "@/components/StepIndicator";
import { useBeforeUnload } from "@/hooks/useBeforeUnload";
import { getOnboardingSessionByEmail, submitCustomQuoteRequest } from "@/lib/api";
import { Box, Typography, Button, CircularProgress } from "@mui/material";

const steps = [
  { number: 1, label: "Email" },
  { number: 2, label: "Pages" },
  { number: 3, label: "Request Quote" },
];

interface Channel {
  id: string;
  url: string;
  type: string;
}

function RequestQuoteStepContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const email = searchParams.get("email") ?? "";

  const [channels, setChannels] = useState<Channel[]>([]);
  const [channelsLoading, setChannelsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const currentStep = 3;

  useBeforeUnload(true);

  useEffect(() => {
    if (!email.trim()) {
      router.replace("/contact");
      return;
    }
    setChannelsLoading(true);
    getOnboardingSessionByEmail(email)
      .then((res) => {
        const data = res.data;
        const pages = data?.session_details?.pages as { channels?: string[] } | undefined;
        const urlList = Array.isArray(pages?.channels) ? pages.channels : [];
        setChannels(
          urlList.map((channelUrl, i) => ({
            id: `review-${i}-${channelUrl}`,
            url: channelUrl,
            type: "Website",
          }))
        );
      })
      .catch(() => setChannels([]))
      .finally(() => setChannelsLoading(false));
  }, [email, router]);

  const handleSubmit = async () => {
    if (!email.trim() || channels.length === 0) return;
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      await submitCustomQuoteRequest(email);
      router.push(
        `/contact/quote/thank-you?email=${encodeURIComponent(email)}`
      );
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : "Something went wrong. Please try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

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
              Review And Submit
            </Typography>
            <Typography
              variant="body1"
              color="text.secondary"
              sx={{
                mt: { xs: 1, sm: 1.5 },
                fontSize: { xs: "0.875rem", sm: "1rem" },
              }}
            >
              Review your contact information and channels below.
            </Typography>
          </Box>

          {/* Review Card */}
          <Box
            sx={{
              mt: { xs: 3, sm: 5 },
              p: { xs: 2, sm: 3 },
              borderRadius: 3,
              border: "1px solid #e5e7eb",
            }}
          >
            {/* Contact Email */}
            <Box>
              <Typography
                variant="caption"
                fontWeight={600}
                color="text.secondary"
                sx={{ textTransform: "uppercase", letterSpacing: "0.05em" }}
              >
                Contact Email
              </Typography>
              <Typography fontWeight={500} sx={{ mt: 0.5 }}>
                {email || "—"}
              </Typography>
            </Box>

            {/* Channels */}
            <Box sx={{ mt: 3 }}>
              <Typography
                variant="caption"
                fontWeight={600}
                color="text.secondary"
                sx={{ textTransform: "uppercase", letterSpacing: "0.05em" }}
              >
                Channels ({channels.length})
              </Typography>
              {channelsLoading ? (
                <Typography color="text.secondary" sx={{ mt: 1.5 }}>
                  Loading…
                </Typography>
              ) : (
              <Box
                sx={{
                  mt: 1.5,
                  display: "flex",
                  flexDirection: "column",
                  gap: 1,
                }}
              >
                {channels.map((channel) => (
                  <Box
                    key={channel.id}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      p: 1.5,
                      borderRadius: 2,
                      border: "1px solid #e5e7eb",
                    }}
                  >
                    <Box
                      sx={{ display: "flex", alignItems: "center", gap: 1.5 }}
                    >
                      <Globe
                        style={{ width: 20, height: 20, color: "#9ca3af" }}
                      />
                      <Typography fontSize="0.875rem">{channel.url}</Typography>
                    </Box>
                    <CheckCircle2
                      style={{ width: 20, height: 20, color: "#4D8AFF" }}
                    />
                  </Box>
                ))}
              </Box>
              )}
            </Box>

            {/* Next Steps Info */}
            <Box
              sx={{
                mt: 3,
                px: 2,
                py: 1.5,
                borderRadius: 2,
                border: "1px solid #f3f4f6",
                bgcolor: "rgba(249, 250, 251, 0.5)",
              }}
            >
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ lineHeight: 1.6 }}
              >
                <span style={{ fontWeight: 600, color: "#3D5A99" }}>
                  Next Steps:
                </span>{" "}
                Our team will review your channels and email a custom quote to{" "}
                <span style={{ fontWeight: 600, color: "#3D5A99" }}>
                  {email || "your email"}
                </span>{" "}
                within 24-48 hours.
              </Typography>
            </Box>
          </Box>

          {submitError && (
            <Typography color="error" sx={{ mt: 2 }} variant="body2">
              {submitError}
            </Typography>
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
              href={email ? `/contact/pages?email=${encodeURIComponent(email)}` : "/contact/pages"}
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
              onClick={handleSubmit}
              disabled={isSubmitting || channelsLoading || channels.length === 0}
              fullWidth
              variant="contained"
              startIcon={
                isSubmitting ? (
                  <CircularProgress size={20} color="inherit" sx={{ flexShrink: 0 }} />
                ) : undefined
              }
              sx={{
                height: 48,
                bgcolor: "#4D8AFF",
                "&:hover": { bgcolor: "#3D7AEF" },
                "&.Mui-disabled": {
                  bgcolor: "rgba(77, 138, 255, 0.6)",
                  color: "rgba(255, 255, 255, 0.9)",
                },
                textTransform: "none",
                fontWeight: 600,
                borderRadius: "9999px",
              }}
            >
              {isSubmitting ? "Submitting..." : "Submit Quote Request"}
            </Button>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

export default function RequestQuoteStep() {
  return (
    <Suspense
      fallback={
        <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "white" }}>
          <CircularProgress />
        </Box>
      }
    >
      <RequestQuoteStepContent />
    </Suspense>
  );
}
