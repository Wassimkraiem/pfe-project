"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { z } from "zod";
import { CheckCircle2 } from "lucide-react";
import StepIndicator from "@/components/StepIndicator";
import { useBeforeUnload } from "@/hooks/useBeforeUnload";
import {
  getOnboardingSessionByEmail,
  getOnboardingSessionChannelsCount,
  getOnboardingSessionPriceId,
  getPaymentPrice,
  SIGNUP_SUCCESS_PATH,
} from "@/lib/api";
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
  { number: 3, label: "Checkout" },
  { number: 4, label: "Account" },
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

function SignupPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");

  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showSigninLink, setShowSigninLink] = useState(false);
  const [loading, setLoading] = useState(false);
  const currentStep = 1;

  useBeforeUnload(email.length > 0);

  const shouldShowSigninLink = (message: string) => {
    const normalized = message.toLowerCase();
    if (normalized.includes("custom quote")) return false;
    return normalized.includes("already") || normalized.includes("in use");
  };

  // After payment success, Lemon Squeezy redirects to /signup?session_id=<SESSION_ID> when user clicks Continue → load step 4 (account)
  useEffect(() => {
    if (!sessionId?.trim()) return;
    // If we're inside the checkout overlay iframe, break out so the top window shows the account page (fixes "stuck loading" after Pay)
    if (typeof window !== "undefined" && window.self !== window.top) {
      const accountUrl = `${SIGNUP_SUCCESS_PATH}/account?session_id=${encodeURIComponent(sessionId)}`;
      window.top!.location.href = accountUrl.startsWith("/") ? `${window.location.origin}${accountUrl}` : accountUrl;
      return;
    }
    router.replace(`${SIGNUP_SUCCESS_PATH}/account?session_id=${encodeURIComponent(sessionId)}`);
  }, [sessionId, router]);

  const handleContinue = async (e: React.MouseEvent) => {
    e.preventDefault();
    setError(null);
    setShowSigninLink(false);
    const result = step1Schema.safeParse({ email });
    if (!result.success) {
      const fieldError = result.error.flatten().fieldErrors.email?.[0];
      const msg = fieldError ?? "Invalid email";
      setError(msg);
      setShowSigninLink(shouldShowSigninLink(msg));
      return;
    }
    setLoading(true);
    try {
      const res = await getOnboardingSessionByEmail(email);
      const data = res.data as { status_code?: number; message?: string; current_step?: string; payment_received?: boolean; custom_quote_submitted?: boolean } | null;
      const nestedStatus = data?.status_code ?? res.status_code;
      const priceId = getOnboardingSessionPriceId(res.data);

      // If current step is account, redirect to account page (user paid but hasn't created account)
      if (data?.current_step === "account") {
        const sessionUuid = res.data?.uuid;
        if (sessionUuid) {
          router.push(`/signup/account?session_id=${encodeURIComponent(sessionUuid)}`);
        } else {
          router.push(`/signup/account?email=${encodeURIComponent(email)}`);
        }
        return;
      }

      // If custom quote is submitted but no price ID set yet, show error
      if (data?.custom_quote_submitted && !priceId) {
        setError("A custom quote is already submitted for this account, please check your email to finish the process.");
        setShowSigninLink(false);
        return;
      }

      if (res.status_code === 202 || nestedStatus === 202) {
        let msg =
          (data?.message as string | undefined) ??
          (res as { message?: string }).message ??
          "This email is already in use.";
        // For custom quote messages, add instruction to check email
        if (msg.toLowerCase().includes("custom quote")) {
          msg = "A custom quote is already submitted for this account, please check your email to finish the process.";
        }
        setError(msg);
        setShowSigninLink(shouldShowSigninLink(msg));
        return;
      }
      if (res.status_code === 400) {
        const msg = (res as { message?: string }).message ?? "Invalid request.";
        setError(msg);
        setShowSigninLink(shouldShowSigninLink(msg));
        return;
      }

      if (priceId) {
        try {
          const priceRes = await getPaymentPrice(priceId);
          if (typeof window !== "undefined") {
            window.sessionStorage.setItem(
              `onboarding_price_${priceId}`,
              JSON.stringify(priceRes.data ?? null)
            );
          }
        } catch {
          // If price fetch fails, checkout can try again later.
        }
      }
      router.push(`/signup/pages?email=${encodeURIComponent(email)}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Something went wrong. Please try again.";
      setError(msg);
      setShowSigninLink(shouldShowSigninLink(msg));
    } finally {
      setLoading(false);
    }
  };

  // While redirecting to account step after payment, show nothing or a brief loading state
  if (sessionId?.trim()) {
    return null;
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
            Let&apos;s Get Started
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
                if (showSigninLink) setShowSigninLink(false);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !loading) {
                  handleContinue(e as unknown as React.MouseEvent);
                }
              }}
              error={!!error}
              helperText={
                error ? (
                  <Box component="span" sx={{ display: "inline-flex", alignItems: "center", gap: 0.5 }}>
                  <Box component="span">{error}</Box>
                  {showSigninLink ? (
                    <>
                      <Box component="span">, please</Box>
                      <Link
                        href="/signin"
                        prefetch={false}
                        style={{
                          textDecoration: "underline",
                          fontWeight: 600,
                          color: "#4D8AFF",
                        }}
                      >
                        sign in
                      </Link>
                    </>
                  ) : null}
                  </Box>
                ) : (
                  " "
                )
              }
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
                borderRadius: 2,
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

export default function SignupPage() {
  return (
    <Suspense
      fallback={
        <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "#fafafa" }}>
          <CircularProgress />
        </Box>
      }
    >
      <SignupPageContent />
    </Suspense>
  );
}
