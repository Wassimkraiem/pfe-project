"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useSignIn } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { ArrowLeft, Check, KeyRound, Lock, Mail } from "lucide-react";
import {
  Box,
  Button,
  CircularProgress,
  TextField,
  Typography,
} from "@mui/material";

const highlights = [
  "Quick password recovery",
  "Secure verification code",
  "Get back to your content",
];

function ForgotPasswordContent() {
  const { signIn, setActive, isLoaded } = useSignIn();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [step, setStep] = useState<"email" | "reset">("email");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleRequestCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!email.trim()) {
      setError("Email is required.");
      return;
    }

    if (!isLoaded || !signIn) {
      setError("Password reset is still loading. Please try again.");
      return;
    }

    setLoading(true);
    try {
      await signIn.create({
        strategy: "reset_password_email_code",
        identifier: email.trim(),
      });
      setStep("reset");
      setSuccess("We sent a verification code to your email.");
    } catch (err) {
      const errorObj = err as {
        errors?: { message?: string; long_message?: string }[];
      };
      const clerkMessage =
        errorObj?.errors?.[0]?.long_message ??
        errorObj?.errors?.[0]?.message ??
        "";
      setError(
        clerkMessage ||
          (err instanceof Error
            ? err.message
            : "Failed to send reset code. Please try again.")
      );
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!code.trim()) {
      setError("Please enter the verification code.");
      return;
    }

    if (!newPassword.trim()) {
      setError("Please enter a new password.");
      return;
    }

    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (!isLoaded || !signIn) {
      setError("Password reset is still loading. Please try again.");
      return;
    }

    setLoading(true);
    try {
      const result = await signIn.attemptFirstFactor({
        strategy: "reset_password_email_code",
        code: code.trim(),
        password: newPassword,
      });

      if (result.status === "complete") {
        await setActive({ session: result.createdSessionId });
        router.replace("/dashboard");
      } else {
        setError(`Password reset requires additional steps (${result.status}).`);
      }
    } catch (err) {
      const errorObj = err as {
        errors?: { message?: string; long_message?: string }[];
      };
      const clerkMessage =
        errorObj?.errors?.[0]?.long_message ??
        errorObj?.errors?.[0]?.message ??
        "";
      setError(
        clerkMessage ||
          (err instanceof Error
            ? err.message
            : "Failed to reset password. Please try again.")
      );
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    setStep("email");
    setCode("");
    setNewPassword("");
    setConfirmPassword("");
    setError(null);
    setSuccess(null);
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
          {/* Info panel: hidden on mobile */}
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
              BVIRAL Password Recovery
            </Typography>
            <Typography
              variant="h4"
              fontWeight="bold"
              sx={{ mt: 2, fontSize: { xs: "1.75rem", sm: "2.25rem" } }}
            >
              Forgot your password?
              <br />
              No worries, we&apos;ve got you.
            </Typography>
            <Typography
              variant="body1"
              color="text.secondary"
              sx={{ mt: 2, maxWidth: "26rem", lineHeight: 1.6 }}
            >
              Enter your email address and we&apos;ll send you a verification
              code to reset your password securely.
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

          {/* Form panel */}
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
            {step === "email" ? (
              <>
                <Typography variant="h5" fontWeight="bold">
                  Reset password
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Enter your email to receive a verification code.
                </Typography>

                <Box
                  component="form"
                  onSubmit={handleRequestCode}
                  sx={{ mt: 3, display: "grid", gap: 2 }}
                >
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
                    error={!!error}
                    helperText={error ?? " "}
                    sx={{ "& .MuiInputBase-root": { minHeight: { xs: 48, sm: 40 } } }}
                    InputProps={{
                      startAdornment: (
                        <Box sx={{ display: "flex", alignItems: "center", mr: 1 }}>
                          <Mail style={{ width: 18, height: 18 }} />
                        </Box>
                      ),
                    }}
                  />

                  <Button
                    variant="contained"
                    fullWidth
                    type="submit"
                    disabled={loading || !isLoaded}
                    sx={{
                      mt: 1,
                      height: 48,
                      bgcolor: "#4D8AFF",
                      "&:hover": { bgcolor: "#3D7AEF" },
                    }}
                  >
                    {loading ? "Sending code..." : "Send reset code"}
                  </Button>
                </Box>
              </>
            ) : (
              <>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                  <Button
                    onClick={handleBack}
                    sx={{
                      minWidth: "auto",
                      p: 0.5,
                      color: "text.secondary",
                      "&:hover": { bgcolor: "rgba(0,0,0,0.04)" },
                    }}
                  >
                    <ArrowLeft style={{ width: 20, height: 20 }} />
                  </Button>
                  <Typography variant="h5" fontWeight="bold">
                    Set new password
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Enter the code sent to <strong>{email}</strong> and your new
                  password.
                </Typography>

                <Box
                  component="form"
                  onSubmit={handleResetPassword}
                  sx={{ mt: 3, display: "grid", gap: 2 }}
                >
                  <TextField
                    label="Verification code"
                    placeholder="000000"
                    value={code}
                    onChange={(e) => {
                      const v = e.target.value.replace(/\D/g, "").slice(0, 6);
                      setCode(v);
                      if (error) setError(null);
                    }}
                    fullWidth
                    inputProps={{
                      inputMode: "numeric",
                      maxLength: 6,
                      autoComplete: "one-time-code",
                    }}
                    sx={{
                      "& .MuiInputBase-root": { minHeight: { xs: 48, sm: 40 } },
                      "& .MuiInputBase-input": {
                        fontSize: "1.25rem",
                        letterSpacing: "0.25em",
                        textAlign: "center",
                      },
                    }}
                    InputProps={{
                      startAdornment: (
                        <Box sx={{ display: "flex", alignItems: "center", mr: 1 }}>
                          <KeyRound style={{ width: 18, height: 18 }} />
                        </Box>
                      ),
                    }}
                  />

                  <TextField
                    label="New password"
                    type="password"
                    placeholder="Enter new password"
                    value={newPassword}
                    onChange={(e) => {
                      setNewPassword(e.target.value);
                      if (error) setError(null);
                    }}
                    fullWidth
                    sx={{ "& .MuiInputBase-root": { minHeight: { xs: 48, sm: 40 } } }}
                    InputProps={{
                      startAdornment: (
                        <Box sx={{ display: "flex", alignItems: "center", mr: 1 }}>
                          <Lock style={{ width: 18, height: 18 }} />
                        </Box>
                      ),
                    }}
                  />

                  <TextField
                    label="Confirm password"
                    type="password"
                    placeholder="Confirm new password"
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      if (error) setError(null);
                    }}
                    fullWidth
                    sx={{ "& .MuiInputBase-root": { minHeight: { xs: 48, sm: 40 } } }}
                    InputProps={{
                      startAdornment: (
                        <Box sx={{ display: "flex", alignItems: "center", mr: 1 }}>
                          <Lock style={{ width: 18, height: 18 }} />
                        </Box>
                      ),
                    }}
                  />

                  {success && (
                    <Typography variant="body2" sx={{ color: "success.main" }}>
                      {success}
                    </Typography>
                  )}

                  <Typography variant="body2" color="error" sx={{ minHeight: 20 }}>
                    {error ?? " "}
                  </Typography>

                  <Button
                    variant="contained"
                    fullWidth
                    type="submit"
                    disabled={loading || !isLoaded}
                    sx={{
                      mt: 1,
                      height: 48,
                      bgcolor: "#4D8AFF",
                      "&:hover": { bgcolor: "#3D7AEF" },
                    }}
                  >
                    {loading ? "Resetting password..." : "Reset password"}
                  </Button>
                </Box>
              </>
            )}

            <Box sx={{ mt: 3, textAlign: "center" }}>
              <Typography variant="body2" color="text.secondary">
                Remember your password?{" "}
                <Link href="/signin" style={{ fontWeight: 600, color: "#4D8AFF" }}>
                  Sign in
                </Link>
              </Typography>
            </Box>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

export default function ForgotPasswordPage() {
  return (
    <Suspense
      fallback={
        <Box
          sx={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            bgcolor: "#f9fafb",
          }}
        >
          <CircularProgress size={40} sx={{ color: "#4D8AFF" }} />
        </Box>
      }
    >
      <ForgotPasswordContent />
    </Suspense>
  );
}
