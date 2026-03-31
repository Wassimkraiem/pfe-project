"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { CheckCircle2 } from "lucide-react";
import StepIndicator from "@/components/StepIndicator";
import { useBeforeUnload } from "@/hooks/useBeforeUnload";
import { getOnboardingSessionByEmail } from "@/lib/api";
import { Box, Typography, TextField, Button, CircularProgress } from "@mui/material";

const step1Schema = z.object({
  email: z
    .string()
    .min(1, "Email is required")
    .email("Please enter a valid email address"),
});

const steps = [
  { number: 1, label: "Email" },
  { number: 2, label: "Pages" },
  { number: 3, label: "Request Quote" },
];

const features = [
  {
    title: "90,000+",
    subtitle: "Videos",
    description: "Access our entire viral content library.",
  },
  {
    title: "Monetization",
    subtitle: "Ready",
    description: "Cleared for monetization on social media.",
  },
  {
    title: "Fresh Content",
    subtitle: "Weekly",
    description: "New viral videos added regularly.",
  },
];

export default function ContactPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const currentStep = 1;

  useBeforeUnload(email.length > 0);

  const handleContinue = async (e: React.MouseEvent) => {
    e.preventDefault();
    setError(null);
    const result = step1Schema.safeParse({ email });
    if (!result.success) {
      const msg = result.error.flatten().fieldErrors.email?.[0] ?? result.error.issues[0]?.message ?? "Invalid email";
      setError(msg);
      return;
    }
    setLoading(true);
    try {
      const res = await getOnboardingSessionByEmail(email);
      const data = res.data as { status_code?: number; message?: string } | null;
      const nestedStatus = data?.status_code ?? res.status_code;
      if (res.status_code === 202 || nestedStatus === 202) {
        const msg =
          (data?.message as string | undefined) ??
          (res as { message?: string }).message ??
          "An email has been sent to you to complete the process.";
        setError(msg);
        return;
      }
      if (res.status_code === 400) {
        setError((res as { message?: string }).message ?? "Invalid request.");
        return;
      }
      router.push(`/contact/pages?email=${encodeURIComponent(email)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
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

        {/* Main Content */}
        <Box
          sx={{
            mt: { xs: 6, sm: 10 },
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            textAlign: "center",
          }}
        >
          <Typography
            variant="h4"
            fontWeight="bold"
            sx={{ fontSize: { xs: "1.5rem", sm: "1.875rem", md: "2.25rem" } }}
          >
            Get a Custom Quote
          </Typography>
          <Typography
            variant="body1"
            color="text.secondary"
            sx={{
              mt: { xs: 1.5, sm: 2 },
              px: { xs: 2, sm: 0 },
              fontSize: { xs: "0.875rem", sm: "1rem" },
            }}
          >
            First, enter your email address. Next, you&apos;ll add your
            channel(s).
          </Typography>

          {/* Email Input */}
          <Box
            sx={{
              mt: { xs: 3, sm: 4 },
              width: "100%",
              maxWidth: "28rem",
              px: { xs: 1, sm: 0 },
            }}
          >
            <TextField
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (error) setError(null);
              }}
              error={!!error}
              helperText={error}
              fullWidth
              required
              sx={{
                "& .MuiOutlinedInput-root": {
                  borderRadius: 2,
                  height: { xs: 44, sm: 48 },
                  "&:hover fieldset": { borderColor: "#4D8AFF" },
                  "&.Mui-focused fieldset": { borderColor: "#4D8AFF" },
                },
              }}
            />

            {/* Continue Button */}
            <Button
              fullWidth
              variant="contained"
              onClick={handleContinue}
              disabled={loading}
              startIcon={
                loading ? (
                  <CircularProgress size={20} color="inherit" sx={{ flexShrink: 0 }} />
                ) : undefined
              }
              sx={{
                mt: 2,
                height: { xs: 44, sm: 48 },
                bgcolor: "#4D8AFF",
                "&:hover": { bgcolor: "#3D7AEF" },
                textTransform: "none",
                fontWeight: 600,
                borderRadius: "9999px",
                fontSize: { xs: "0.875rem", sm: "1rem" },
              }}
            >
              {loading ? "Checking…" : "Continue"}
            </Button>
          </Box>
        </Box>

        {/* Divider */}
        <Box
          sx={{
            mx: "auto",
            mt: { xs: 5, sm: 8 },
            maxWidth: "28rem",
            borderTop: "1px solid #e5e7eb",
          }}
        />

        {/* Features */}
        <Box
          sx={{
            mx: "auto",
            mt: { xs: 4, sm: 6 },
            maxWidth: "28rem",
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: { xs: 2, sm: 4 },
            px: { xs: 1, sm: 0 },
          }}
        >
          {features.map((feature) => (
            <Box
              key={feature.title}
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: { xs: "center", sm: "flex-start" },
                textAlign: { xs: "center", sm: "left" },
              }}
            >
              <CheckCircle2
                style={{ width: 20, height: 20, color: "#4D8AFF" }}
                strokeWidth={1.5}
              />
              <Typography
                fontWeight="bold"
                sx={{
                  mt: { xs: 1, sm: 1.5 },
                  fontSize: { xs: "0.875rem", sm: "1rem" },
                  lineHeight: 1.3,
                }}
              >
                {feature.title}
                <br />
                {feature.subtitle}
              </Typography>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{
                  mt: { xs: 0.5, sm: 1 },
                  fontSize: { xs: "10px", sm: "0.75rem" },
                }}
              >
                {feature.description}
              </Typography>
            </Box>
          ))}
        </Box>

        {/* Terms */}
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            mx: "auto",
            mt: { xs: 5, sm: 8 },
            maxWidth: "28rem",
            px: { xs: 2, sm: 0 },
            textAlign: "center",
            fontSize: { xs: "0.75rem", sm: "0.875rem" },
          }}
        >
          By continuing, you agree to BVIRAL&apos;s{" "}
          <Link
            href="https://bviral.com/terms-of-use/"
            target="_blank"
            rel="noopener noreferrer"
            style={{ textDecoration: "underline", color: "inherit" }}
          >
            Terms of Use
          </Link>{" "}
          and{" "}
          <Link
            href="https://bviral.com/privacy-policy/"
            target="_blank"
            rel="noopener noreferrer"
            style={{ textDecoration: "underline", color: "inherit" }}
          >
            Privacy Policy
          </Link>
          .
        </Typography>
      </Box>
    </Box>
  );
}
