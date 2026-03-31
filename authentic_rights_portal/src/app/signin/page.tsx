"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useAuth, useSignIn } from "@clerk/nextjs";
import { useRouter, useSearchParams } from "next/navigation";
import { Check, Lock, Mail } from "lucide-react";
import {
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Divider,
  FormControlLabel,
  TextField,
  Typography,
} from "@mui/material";

const highlights = [
  "Approved for monetization",
  "Watermark-free downloads",
  "Weekly content drops",
];

function getSafeRedirect(redirect: string | null): string {
  if (!redirect || typeof redirect !== "string") return "/dashboard";
  const path = redirect.startsWith("/") ? redirect : `/${redirect}`;
  return path.split("?")[0] || "/dashboard";
}

function SigninPageContent() {
  const { signIn, setActive, isLoaded } = useSignIn();
  const { isSignedIn, isLoaded: authLoaded } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTo = getSafeRedirect(searchParams.get("redirect"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [needsSecondFactor, setNeedsSecondFactor] = useState(false);
  const [supportedFactors, setSupportedFactors] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    const emailParam = searchParams.get("email");
    if (emailParam && typeof emailParam === "string") {
      setEmail(decodeURIComponent(emailParam));
    }
  }, [searchParams]);

  useEffect(() => {
    if (authLoaded && isSignedIn) {
      router.replace(redirectTo);
    }
  }, [authLoaded, isSignedIn, router, redirectTo]);

  const handleSignin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setNeedsSecondFactor(false);
    if (!email.trim() || !password.trim()) {
      setError("Email and password are required.");
      return;
    }
    if (!isLoaded || !signIn) {
      setError("Sign in is still loading. Please try again.");
      return;
    }
    setLoading(true);
    try {
      const result = await signIn.create({
        identifier: email.trim(),
        password,
      });
      if (result.status === "complete") {
        await setActive({ session: result.createdSessionId });
        router.replace(redirectTo);
        return;
      }
      if (result.status === "needs_second_factor") {
        const supportedRaw = result.supportedSecondFactors ?? [];
        const supported = supportedRaw
          .map((factor) =>
            typeof factor === "string"
              ? factor
              : typeof factor === "object" && factor
                ? String((factor as { strategy?: string }).strategy ?? "")
                : ""
          )
          .filter(Boolean);
        setSupportedFactors(supported);
        if (supported.includes("email_code")) {
          await signIn.prepareSecondFactor({ strategy: "email_code" });
          setNeedsSecondFactor(true);
          setError("We sent a verification code to your email.");
          return;
        }
        const readable = supported.length ? supported.join(", ") : "none";
        setError(
          `Second-factor verification is required, but email codes are not supported. Supported factors: ${readable}.`
        );
        return;
      }
      setError(`Sign in requires additional verification (${result.status}).`);
    } catch (err) {
      const errorObj = err as {
        errors?: { message?: string; long_message?: string }[];
      };
      const clerkMessage =
        errorObj?.errors?.[0]?.long_message ?? errorObj?.errors?.[0]?.message ?? "";
      const message =
        clerkMessage ||
        (err instanceof Error ? err.message : "Sign in failed. Please try again.");
      const msgLower = String(message).toLowerCase();
      if (msgLower.includes("session already exists") || msgLower.includes("already signed in")) {
        router.replace(redirectTo);
        return;
      }
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!isLoaded || !signIn) return;
    if (!code.trim()) {
      setError("Please enter the verification code.");
      return;
    }
    setVerifying(true);
    try {
      const attempt = await signIn.attemptSecondFactor({
        strategy: "email_code",
        code: code.trim(),
      });
      if (attempt.status === "complete") {
        await setActive({ session: attempt.createdSessionId });
        router.replace(redirectTo);
        return;
      }
      setError(`Verification not complete (${attempt.status}).`);
    } catch (err) {
      const errorObj = err as {
        errors?: { message?: string; long_message?: string }[];
      };
      const clerkMessage =
        errorObj?.errors?.[0]?.long_message ?? errorObj?.errors?.[0]?.message ?? "";
      const message =
        clerkMessage ||
        (err instanceof Error ? err.message : "Verification failed. Please try again.");
      const msgLower = String(message).toLowerCase();
      if (msgLower.includes("session already exists") || msgLower.includes("already signed in")) {
        router.replace(redirectTo);
        return;
      }
      setError(message);
    } finally {
      setVerifying(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "#f9fafb",
        py: { xs: 3, sm: 6, md: 8 },
        px: { xs: 0, sm: 3 },
        pb: { xs: "max(24px, env(safe-area-inset-bottom))", sm: undefined },
      }}
    >
      <Box
        sx={{
          maxWidth: "72rem",
          mx: "auto",
          px: { xs: 2, sm: 0, lg: 4 },
        }}
      >
        <Box
          sx={{
            display: "grid",
            gap: { xs: 0, md: 6 },
            gridTemplateColumns: { md: "1.1fr 1fr" },
            alignItems: "stretch",
          }}
        >
          {/* Info panel: hidden on mobile so user focuses only on form */}
          <Box
            sx={{
              display: { xs: "none", md: "block" },
              bgcolor: "white",
              borderRadius: 4,
              p: { xs: 3, sm: 4 },
              border: "1px solid #e5e7eb",
              background:
                "linear-gradient(135deg, rgba(239, 246, 255, 0.9) 0%, #ffffff 65%)",
            }}
          >
            <Typography
              variant="body2"
              fontWeight={600}
              sx={{ color: "#4D8AFF" }}
            >
              BVIRAL Member Access
            </Typography>
            <Typography
              variant="h4"
              fontWeight="bold"
              sx={{ mt: 2, fontSize: { xs: "1.75rem", sm: "2.25rem" } }}
            >
              Welcome back.
              <br />
              Let&apos;s keep your growth moving.
            </Typography>
            <Typography
              variant="body1"
              color="text.secondary"
              sx={{ mt: 2, maxWidth: "26rem", lineHeight: 1.6 }}
            >
              Sign in to access your licensed content library, manage channels,
              and track your subscription status.
            </Typography>

            <Box sx={{ mt: 4, display: "flex", flexDirection: "column", gap: 2 }}>
              {highlights.map((item) => (
                <Box
                  key={item}
                  sx={{ display: "flex", alignItems: "center", gap: 1.5 }}
                >
                  <Box
                    sx={{
                      width: 32,
                      height: 32,
                      borderRadius: "50%",
                      bgcolor: "rgba(77, 138, 255, 0.12)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <Check style={{ width: 16, height: 16, color: "#4D8AFF" }} />
                  </Box>
                  <Typography fontWeight={500}>{item}</Typography>
                </Box>
              ))}
            </Box>
          </Box>

          {/* Sign-in form: first on mobile, right column on desktop */}
          <Box
            sx={{
              bgcolor: "white",
              borderRadius: { xs: 0, sm: 4 },
              p: { xs: 3, sm: 4 },
              border: { xs: "none", sm: "1px solid #e5e7eb" },
              boxShadow: { xs: "none", sm: "0 1px 3px rgba(0,0,0,0.06)" },
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              minHeight: { xs: "auto", md: 420 },
            }}
          >
            <Typography variant="h5" fontWeight="bold">
              Sign in
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Use the account linked to your BVIRAL subscription.
            </Typography>

            <Box component="form" onSubmit={handleSignin} sx={{ mt: 3, display: "grid", gap: 2 }}>
              <TextField
                label="Email"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (error) setError(null);
                }}
                fullWidth
                error={!needsSecondFactor && !!error}
                helperText={error ? " " : " "}
                disabled={needsSecondFactor}
                sx={{ "& .MuiInputBase-root": { minHeight: { xs: 48, sm: 40 } } }}
                InputProps={{
                  startAdornment: (
                    <Box sx={{ display: "flex", alignItems: "center", mr: 1 }}>
                      <Mail style={{ width: 18, height: 18 }} />
                    </Box>
                  ),
                }}
              />
              <TextField
                label="Password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (error) setError(null);
                }}
                fullWidth
                error={!needsSecondFactor && !!error}
                disabled={needsSecondFactor}
                sx={{ "& .MuiInputBase-root": { minHeight: { xs: 48, sm: 40 } } }}
                InputProps={{
                  startAdornment: (
                    <Box sx={{ display: "flex", alignItems: "center", mr: 1 }}>
                      <Lock style={{ width: 18, height: 18 }} />
                    </Box>
                  ),
                }}
              />
              {needsSecondFactor ? (
                <TextField
                  label="Verification code"
                  placeholder="000000"
                  value={code}
                  onChange={(e) => {
                    const v = e.target.value.replace(/\D/g, "").slice(0, 6);
                    setCode(v);
                    if (error) setError(null);
                  }}
                  helperText="Check your email for the 6-digit code we sent you."
                  fullWidth
                  inputProps={{
                    inputMode: "numeric",
                    maxLength: 6,
                    autoComplete: "one-time-code",
                    "aria-label": "Verification code from email",
                  }}
                  sx={{
                    "& .MuiInputBase-root": { minHeight: { xs: 48, sm: 40 } },
                    "& .MuiInputBase-input": { fontSize: "1.25rem", letterSpacing: "0.25em", textAlign: "center" },
                  }}
                />
              ) : null}
              <Typography variant="body2" color="error" sx={{ minHeight: 20 }}>
                {error ?? " "}
              </Typography>

              {needsSecondFactor ? (
                <Button
                  variant="contained"
                  fullWidth
                  onClick={handleVerifyCode}
                  disabled={verifying || !isLoaded}
                  sx={{ mt: 1, height: 48, bgcolor: "#4D8AFF", "&:hover": { bgcolor: "#3D7AEF" } }}
                >
                  {verifying ? "Verifying..." : "Verify code"}
                </Button>
              ) : (
                <Button
                  variant="contained"
                  fullWidth
                  type="submit"
                  disabled={loading || !isLoaded}
                  sx={{ mt: 1, height: 48, bgcolor: "#4D8AFF", "&:hover": { bgcolor: "#3D7AEF" } }}
                >
                  {loading ? "Signing in..." : "Sign in"}
                </Button>
              )}
            </Box>

            <Box
              sx={{
                mt: 2,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: 1,
              }}
            >
              <FormControlLabel
                control={<Checkbox size="small" />}
                label={<Typography variant="body2">Remember me</Typography>}
              />
              <Link href="/forgot-password" style={{ fontSize: "0.875rem" }}>
                Forgot password?
              </Link>
            </Box>

            <Divider sx={{ my: 3 }} />

            <Typography variant="body2" color="text.secondary">
              New to BVIRAL?{" "}
              <Link href="/signup" style={{ fontWeight: 600 }}>
                Create an account
              </Link>
            </Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

export default function SigninPage() {
  return (
    <Suspense
      fallback={
        <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "#f9fafb" }}>
          <CircularProgress size={40} sx={{ color: "#4D8AFF" }} />
        </Box>
      }
    >
      <SigninPageContent />
    </Suspense>
  );
}
