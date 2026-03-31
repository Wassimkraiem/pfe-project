"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams, notFound } from "next/navigation";
import { z } from "zod";
import { Check, User, Building2, Eye, EyeOff } from "lucide-react";
import StepIndicator from "@/components/StepIndicator";
import { useBeforeUnload } from "@/hooks/useBeforeUnload";
import { getOnboardingSessionByUuid, completeOnboardingAccount } from "@/lib/api";
import { useSignIn } from "@clerk/nextjs";
import { Box, Typography, TextField, Button, CircularProgress, IconButton, InputAdornment } from "@mui/material";

const SESSION_VALIDATION_MAX_WAIT_MS = 45000;
const SESSION_VALIDATION_RETRY_MS = 2500;

const passwordSchema = z
  .string()
  .min(8, "Password must be at least 8 characters")
  .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
  .regex(/[a-z]/, "Password must contain at least one lowercase letter")
  .regex(/\d/, "Password must contain at least one digit")
  .regex(/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/, "Password must contain at least one special character");

const accountFormSchema = z
  .object({
    first_name: z.string().min(1, "First name is required").trim(),
    last_name: z.string().min(1, "Last name is required").trim(),
    account_type: z.enum(["individual", "business"]),
    company_name: z.string().optional(),
    password: passwordSchema,
    confirm_password: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  })
  .refine(
    (data) => {
      if (data.account_type === "business") {
        return (data.company_name ?? "").trim().length > 0;
      }
      return true;
    },
    { message: "Company name is required for business accounts", path: ["company_name"] }
  );

type AccountFormValues = z.infer<typeof accountFormSchema>;

const steps = [
  { number: 1, label: "Email" },
  { number: 2, label: "Pages" },
  { number: 3, label: "Checkout" },
  { number: 4, label: "Account" },
];

type AccountType = "individual" | "business";

function AccountStepContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id") ?? "";
  const { signIn, setActive, isLoaded: signInLoaded } = useSignIn();

  const [accountType, setAccountType] = useState<AccountType>("individual");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sessionValid, setSessionValid] = useState<boolean | null>(null);
  const [sessionEmail, setSessionEmail] = useState<string | null>(null);
  const [accountAlreadyCompleted, setAccountAlreadyCompleted] = useState(false);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof AccountFormValues, string>>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [pendingSignIn, setPendingSignIn] = useState<{ email: string; password: string } | null>(null);
  const [needsVerificationCode, setNeedsVerificationCode] = useState(false);
  const [verificationCode, setVerificationCode] = useState("");
  const [verifyingCode, setVerifyingCode] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [isResending, setIsResending] = useState(false);
  const currentStep = 4;

  useBeforeUnload(true);

  const passwordChecks = [
    { label: "At least 8 characters", met: password.length >= 8 },
    { label: "One uppercase letter", met: /[A-Z]/.test(password) },
    { label: "One lowercase letter", met: /[a-z]/.test(password) },
    { label: "One number", met: /\d/.test(password) },
    { label: "One special character (!@#$%^&*)", met: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password) },
  ];

  const startResendCooldown = () => {
    setResendCooldown(30);
  };

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => {
        if (prev <= 1) { clearInterval(timer); return 0; }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  const handleResendCode = async () => {
    if (!signIn || isResending || resendCooldown > 0) return;
    setIsResending(true);
    setSubmitError(null);
    try {
      await signIn.prepareSecondFactor({ strategy: "email_code" });
      setVerificationCode("");
      startResendCooldown();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to resend code. Please try again.");
    } finally {
      setIsResending(false);
    }
  };

  // If we're inside the checkout overlay iframe (e.g. after Lemon Squeezy redirect), break out so user sees full page
  useEffect(() => {
    if (typeof window !== "undefined" && window.self !== window.top && sessionId) {
      window.top!.location.href = window.location.href;
    }
  }, [sessionId]);

  // Validate session via GET /onboarding_sessions/{session_uuid}; if 200 with session data, show step 4 (account)
  useEffect(() => {
    if (!sessionId.trim()) {
      notFound();
      return;
    }
    let cancelled = false;
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;
    const startedAt = Date.now();

    const validateSession = async (): Promise<void> => {
      try {
        const res = await getOnboardingSessionByUuid(sessionId.trim());
        if (cancelled) return;

        const step = res.data?.current_step;
        const isCompleted = step === "complete" || step === "completed" || step === "done";

        // If account creation is already completed, show friendly message instead of 404
        if (res.status_code === 200 && isCompleted) {
          setSessionEmail(res.data?.email ?? null);
          setAccountAlreadyCompleted(true);
          setSessionValid(false);
          return;
        }

        const readyForAccount =
          res.status_code === 200 && res.data?.payment_received === true && step === "account";
        if (readyForAccount) {
          setSessionValid(true);
          setSessionEmail(res.data?.email ?? null);
          return;
        }

        // Stripe redirects can beat webhook processing; retry briefly before failing.
        const shouldRetry = Date.now() - startedAt < SESSION_VALIDATION_MAX_WAIT_MS;
        if (shouldRetry) {
          setSessionValid(null);
          retryTimeout = setTimeout(validateSession, SESSION_VALIDATION_RETRY_MS);
          return;
        }

        setSessionValid(false);
        notFound();
      } catch {
        if (cancelled) return;
        const shouldRetry = Date.now() - startedAt < SESSION_VALIDATION_MAX_WAIT_MS;
        if (shouldRetry) {
          setSessionValid(null);
          retryTimeout = setTimeout(validateSession, SESSION_VALIDATION_RETRY_MS);
          return;
        }
        setSessionValid(false);
        notFound();
      }
    };

    void validateSession();
    return () => {
      cancelled = true;
      if (retryTimeout) clearTimeout(retryTimeout);
    };
  }, [sessionId]);

  // When Clerk becomes ready after account creation, try sign-in with pending credentials
  useEffect(() => {
    if (!signInLoaded || !signIn || !pendingSignIn || !setActive) return;
    const { email, password } = pendingSignIn;
    let cancelled = false;
    (async () => {
      try {
        const result = await signIn.create({ identifier: email, password });
        if (cancelled) return;
        setPendingSignIn(null);
        if (result.status === "complete") {
          await setActive({ session: result.createdSessionId });
          router.replace("/dashboard");
          return;
        }
        if (result.status === "needs_second_factor" && signIn.supportedSecondFactors?.some((f) => (typeof f === "string" ? f : (f as { strategy?: string }).strategy) === "email_code")) {
          await signIn.prepareSecondFactor({ strategy: "email_code" });
          setNeedsVerificationCode(true);
          startResendCooldown();
          setSubmitError(null);
          setFormErrors({});
        } else {
          setSubmitError("Account created. Please complete sign-in to continue.");
        }
        setIsSubmitting(false);
      } catch (err) {
        if (cancelled) return;
        setPendingSignIn(null);
        setSubmitError(err instanceof Error ? err.message : "Sign-in failed. You can sign in from the sign-in page.");
        setIsSubmitting(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [signInLoaded, signIn, pendingSignIn, setActive, router]);

  const handleSubmit = () => {
    setSubmitError(null);
    setFormErrors({});
    const payload: AccountFormValues = {
      first_name: firstName,
      last_name: lastName,
      account_type: accountType,
      company_name: accountType === "business" ? companyName : undefined,
      password,
      confirm_password: confirmPassword,
    };
    const result = accountFormSchema.safeParse(payload);
    if (!result.success) {
      const flattened = result.error.flatten().fieldErrors;
      const fieldErrors: Partial<Record<keyof AccountFormValues, string>> = {};
      Object.entries(flattened).forEach(([key, messages]) => {
        const msg = Array.isArray(messages) ? messages[0] : messages;
        if (msg) fieldErrors[key as keyof AccountFormValues] = msg;
      });
      setFormErrors(fieldErrors);
      return;
    }
    const data = result.data;
    setIsSubmitting(true);
    completeOnboardingAccount(sessionId.trim(), {
      first_name: data.first_name,
      last_name: data.last_name,
      account_type: data.account_type,
      company_name: data.account_type === "business" ? (data.company_name ?? "") : null,
      password: data.password,
      confirm_password: data.confirm_password,
    })
      .then(async () => {
        const email = sessionEmail?.trim();
        if (!email) {
          router.replace("/signin?redirect=/dashboard");
          return;
        }
        if (!signInLoaded || !signIn) {
          setPendingSignIn({ email, password });
          return;
        }
        try {
          const result = await signIn.create({ identifier: email, password });
          if (result.status === "complete") {
            await setActive?.({ session: result.createdSessionId });
            router.replace("/dashboard");
            return;
          }
          if (result.status === "needs_second_factor") {
            const supportsEmailCode = result.supportedSecondFactors?.some(
              (f) => (typeof f === "string" ? f : (f as { strategy?: string }).strategy) === "email_code"
            );
            if (supportsEmailCode) {
              await signIn.prepareSecondFactor({ strategy: "email_code" });
              setNeedsVerificationCode(true);
              startResendCooldown();
              setSubmitError(null);
              setFormErrors({});
            } else {
              setSubmitError("Account created. Please sign in to complete verification.");
              router.replace(`/signin?email=${encodeURIComponent(email)}&redirect=/dashboard`);
            }
            return;
          }
          setSubmitError("Account created. Please sign in to continue.");
          router.replace(`/signin?email=${encodeURIComponent(email)}&redirect=/dashboard`);
        } catch (err) {
          const message =
            err instanceof Error
              ? err.message
              : "Account created, but we couldn't sign you in automatically. Please sign in.";
          setSubmitError(message);
          router.replace(`/signin?email=${encodeURIComponent(email)}&redirect=/dashboard`);
        }
      })
      .catch((err) => {
        setSubmitError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
        if (err instanceof Error && err.message.includes("UUID")) {
          setSessionValid(false);
          notFound();
        }
      })
      .finally(() => {
        setIsSubmitting(false);
      });
  };

  const handleVerifyCode = async () => {
    if (!signIn || !verificationCode.trim() || verifyingCode) return;
    setSubmitError(null);
    setVerifyingCode(true);
    try {
      const attempt = await signIn.attemptSecondFactor({
        strategy: "email_code",
        code: verificationCode.trim(),
      });
      if (attempt.status === "complete" && setActive) {
        await setActive({ session: attempt.createdSessionId });
        router.replace("/dashboard");
        return;
      }
      setSubmitError(attempt.status ? `Verification incomplete (${attempt.status}).` : "Verification failed. Please try again.");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Verification failed. Please try again.";
      setSubmitError(msg);
    } finally {
      setVerifyingCode(false);
    }
  };

  // Wait for session validation before rendering step 4 or triggering 404
  if (sessionValid === null && !accountAlreadyCompleted) {
    return (
      <Box sx={{ minHeight: "100vh", bgcolor: "white", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Typography color="text.secondary">Finalizing your payment...</Typography>
        <Typography color="text.secondary">Please don&apos;t close this tab.</Typography>
      </Box>
    );
  }

  // Show friendly message when account is already created
  if (accountAlreadyCompleted) {
    const signInUrl = sessionEmail
      ? `/signin?email=${encodeURIComponent(sessionEmail)}&redirect=/dashboard`
      : "/signin?redirect=/dashboard";
    return (
      <Box
        sx={{
          minHeight: "100vh",
          bgcolor: "white",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          px: 2,
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 56,
            height: 56,
            borderRadius: "50%",
            bgcolor: "#dcfce7",
            mb: 3,
          }}
        >
          <Check style={{ width: 28, height: 28, color: "#22c55e" }} strokeWidth={3} />
        </Box>
        <Typography variant="h5" fontWeight="bold" color="text.primary">
          Account Already Created
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5, textAlign: "center", maxWidth: 400 }}>
          You&apos;ve already completed your account setup. Please sign in to access your dashboard.
        </Typography>
        <Button
          component={Link}
          href={signInUrl}
          variant="contained"
          sx={{
            mt: 3,
            bgcolor: "#4D8AFF",
            "&:hover": { bgcolor: "#3D7AEF" },
            textTransform: "none",
            fontWeight: 600,
            borderRadius: 2,
            px: 4,
            py: 1.25,
          }}
        >
          Sign in to your account
        </Button>
      </Box>
    );
  }

  if (sessionValid === false) {
    // Show 404 message inline until notFound() renders the not-found page
    return (
      <Box
        sx={{
          minHeight: "100vh",
          bgcolor: "white",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          px: 2,
        }}
      >
        <Typography variant="h5" fontWeight="bold" color="text.primary">
          Session not found
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1, textAlign: "center" }}>
          The link may be invalid or expired.
        </Typography>
        <Button
          component={Link}
          href="/signup"
          variant="contained"
          sx={{
            mt: 3,
            bgcolor: "#4D8AFF",
            "&:hover": { bgcolor: "#3D7AEF" },
            textTransform: "none",
            fontWeight: 600,
            borderRadius: 2,
          }}
        >
          Back to signup
        </Button>
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
        <Box sx={{ mx: "auto", mt: { xs: 4, sm: 6 }, maxWidth: "36rem" }}>
          {/* Account Form Card */}
          <Box
            sx={{
              p: { xs: 2, sm: 4 },
              borderRadius: 3,
              border: "1px solid #e5e7eb",
            }}
          >
            {/* Success Icon */}
            <Box sx={{ display: "flex", justifyContent: "center" }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: { xs: 48, sm: 56 },
                  height: { xs: 48, sm: 56 },
                  borderRadius: "50%",
                  bgcolor: "#dcfce7",
                }}
              >
                <Check
                  style={{ width: 24, height: 24, color: "#22c55e" }}
                  strokeWidth={3}
                />
              </Box>
            </Box>

            {/* Title */}
            <Typography
              variant="h5"
              fontWeight="bold"
              sx={{
                mt: { xs: 2, sm: 2.5 },
                textAlign: "center",
                fontSize: { xs: "1.25rem", sm: "1.5rem", md: "1.875rem" },
              }}
            >
              Almost There!
            </Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{
                mt: 1,
                textAlign: "center",
                fontSize: { xs: "0.75rem", sm: "0.875rem" },
              }}
            >
              Complete your account to instantly access 90,000+ viral videos.
            </Typography>

            {/* Account Type Selector */}
            <Box sx={{ mt: { xs: 3, sm: 4 } }}>
              <Typography fontWeight={600} fontSize="0.875rem">
                Account Type
              </Typography>
              <Box
                sx={{
                  mt: 1,
                  display: "grid",
                  gridTemplateColumns: "repeat(2, 1fr)",
                  gap: { xs: 1, sm: 1.5 },
                }}
              >
                <Button
                  onClick={() => {
                    setAccountType("individual");
                    setFormErrors((prev) => ({ ...prev, company_name: undefined }));
                  }}
                  variant="outlined"
                  startIcon={<User style={{ width: 16, height: 16 }} />}
                  sx={{
                    py: { xs: 1.25, sm: 1.5 },
                    textTransform: "none",
                    fontWeight: 500,
                    fontSize: { xs: "0.75rem", sm: "0.875rem" },
                    borderWidth: 2,
                    borderColor:
                      accountType === "individual" ? "#4D8AFF" : "#e5e7eb",
                    bgcolor:
                      accountType === "individual"
                        ? "rgba(77, 138, 255, 0.05)"
                        : "transparent",
                    color: accountType === "individual" ? "#4D8AFF" : "#111827",
                    "&:hover": {
                      borderColor:
                        accountType === "individual" ? "#4D8AFF" : "#d1d5db",
                      bgcolor:
                        accountType === "individual"
                          ? "rgba(77, 138, 255, 0.05)"
                          : "transparent",
                    },
                  }}
                >
                  Individual
                </Button>
                <Button
                  onClick={() => {
                    setAccountType("business");
                    setFormErrors((prev) => ({ ...prev, company_name: undefined }));
                  }}
                  variant="outlined"
                  startIcon={<Building2 style={{ width: 16, height: 16 }} />}
                  sx={{
                    py: { xs: 1.25, sm: 1.5 },
                    textTransform: "none",
                    fontWeight: 500,
                    fontSize: { xs: "0.75rem", sm: "0.875rem" },
                    borderWidth: 2,
                    borderColor:
                      accountType === "business" ? "#4D8AFF" : "#e5e7eb",
                    bgcolor:
                      accountType === "business"
                        ? "rgba(77, 138, 255, 0.05)"
                        : "transparent",
                    color: accountType === "business" ? "#4D8AFF" : "#111827",
                    "&:hover": {
                      borderColor:
                        accountType === "business" ? "#4D8AFF" : "#d1d5db",
                      bgcolor:
                        accountType === "business"
                          ? "rgba(77, 138, 255, 0.05)"
                          : "transparent",
                    },
                  }}
                >
                  Business
                </Button>
              </Box>
            </Box>

            {/* Form Fields */}
            <Box
              sx={{
                mt: { xs: 2.5, sm: 3 },
                display: "flex",
                flexDirection: "column",
                gap: { xs: 2, sm: 2.5 },
              }}
            >
              {accountType === "business" && (
                <Box>
                  <Typography fontWeight={600} fontSize="0.875rem">
                    Company Name
                  </Typography>
                  <TextField
                    type="text"
                    placeholder="Your company or brand name"
                    value={companyName}
                    onChange={(e) => {
                      setCompanyName(e.target.value);
                      if (formErrors.company_name) setFormErrors((prev) => ({ ...prev, company_name: undefined }));
                    }}
                    error={!!formErrors.company_name}
                    helperText={formErrors.company_name}
                    fullWidth
                    size="small"
                    sx={{
                      mt: 1,
                      "& .MuiOutlinedInput-root": {
                        borderRadius: 2,
                        height: { xs: 40, sm: 44 },
                      },
                    }}
                  />
                </Box>
              )}

              {/* Name Fields */}
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
                  gap: { xs: 2, sm: 1.5 },
                }}
              >
                <Box>
                  <Typography fontWeight={600} fontSize="0.875rem">
                    {accountType === "business"
                      ? "Contact First Name"
                      : "First Name"}
                  </Typography>
                  <TextField
                    type="text"
                    value={firstName}
                    onChange={(e) => {
                      setFirstName(e.target.value);
                      if (formErrors.first_name) setFormErrors((prev) => ({ ...prev, first_name: undefined }));
                    }}
                    error={!!formErrors.first_name}
                    helperText={formErrors.first_name}
                    fullWidth
                    size="small"
                    sx={{
                      mt: 1,
                      "& .MuiOutlinedInput-root": {
                        borderRadius: 2,
                        height: { xs: 40, sm: 44 },
                      },
                    }}
                  />
                </Box>
                <Box>
                  <Typography fontWeight={600} fontSize="0.875rem">
                    {accountType === "business"
                      ? "Contact Last Name"
                      : "Last Name"}
                  </Typography>
                  <TextField
                    type="text"
                    value={lastName}
                    onChange={(e) => {
                      setLastName(e.target.value);
                      if (formErrors.last_name) setFormErrors((prev) => ({ ...prev, last_name: undefined }));
                    }}
                    error={!!formErrors.last_name}
                    helperText={formErrors.last_name}
                    fullWidth
                    size="small"
                    sx={{
                      mt: 1,
                      "& .MuiOutlinedInput-root": {
                        borderRadius: 2,
                        height: { xs: 40, sm: 44 },
                      },
                    }}
                  />
                </Box>
              </Box>

              {accountType === "business" && (
                <Typography variant="caption" color="text.secondary">
                  Primary contact person for account and billing communications
                </Typography>
              )}

              {/* Password Fields */}
              <Box>
                <Typography fontWeight={600} fontSize="0.875rem">
                  Create Password
                </Typography>
                <TextField
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter a strong password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (formErrors.password) setFormErrors((prev) => ({ ...prev, password: undefined }));
                  }}
                  error={!needsVerificationCode && !!formErrors.password}
                  helperText={!needsVerificationCode ? (formErrors.password ?? undefined) : undefined}
                  fullWidth
                  size="small"
                  sx={{
                    mt: 1,
                    "& .MuiOutlinedInput-root": {
                      borderRadius: 2,
                      height: { xs: 40, sm: 44 },
                    },
                  }}
                  InputProps={{
                    autoComplete: "new-password",
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          type="button"
                          aria-label={showPassword ? "Hide password" : "Show password"}
                          onClick={() => setShowPassword((prev) => !prev)}
                          edge="end"
                          size="small"
                          sx={{ color: "text.secondary" }}
                        >
                          {showPassword ? (
                            <EyeOff style={{ width: 18, height: 18 }} />
                          ) : (
                            <Eye style={{ width: 18, height: 18 }} />
                          )}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
                <Box sx={{ mt: 1.5, display: "flex", flexDirection: "column", gap: 0.5 }}>
                  {passwordChecks.map(({ label, met }) => (
                    <Box
                      key={label}
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                        fontSize: "0.8125rem",
                        color: met ? "text.secondary" : "text.disabled",
                      }}
                    >
                      {met ? (
                        <Check style={{ width: 14, height: 14, color: "#10b981", flexShrink: 0 }} />
                      ) : (
                        <Box
                          sx={{
                            width: 14,
                            height: 14,
                            borderRadius: "50%",
                            border: "1.5px solid",
                            borderColor: "rgba(0,0,0,0.2)",
                            flexShrink: 0,
                          }}
                        />
                      )}
                      <span>{label}</span>
                    </Box>
                  ))}
                </Box>
              </Box>

              <Box>
                <Typography fontWeight={600} fontSize="0.875rem">
                  Confirm Password
                </Typography>
                <TextField
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="Re-enter your password"
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    if (formErrors.confirm_password) setFormErrors((prev) => ({ ...prev, confirm_password: undefined }));
                  }}
                  error={!needsVerificationCode && !!formErrors.confirm_password}
                  helperText={!needsVerificationCode ? formErrors.confirm_password : undefined}
                  fullWidth
                  size="small"
                  sx={{
                    mt: 1,
                    "& .MuiOutlinedInput-root": {
                      borderRadius: 2,
                      height: { xs: 40, sm: 44 },
                    },
                  }}
                  InputProps={{
                    autoComplete: "new-password",
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          type="button"
                          aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                          onClick={() => setShowConfirmPassword((prev) => !prev)}
                          edge="end"
                          size="small"
                          sx={{ color: "text.secondary" }}
                        >
                          {showConfirmPassword ? (
                            <EyeOff style={{ width: 18, height: 18 }} />
                          ) : (
                            <Eye style={{ width: 18, height: 18 }} />
                          )}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
              </Box>
            </Box>

            {submitError && (
              <Typography color="error" fontSize="0.875rem" sx={{ mt: 1 }}>
                {submitError}
              </Typography>
            )}

            {needsVerificationCode ? (
              <Box sx={{ mt: 3, p: 2, bgcolor: "rgba(77, 138, 255, 0.06)", borderRadius: 2, border: "1px solid rgba(77, 138, 255, 0.2)" }}>
                <Typography fontWeight={600} fontSize="0.875rem" sx={{ mb: 1 }}>
                  Check your email
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  We just sent a 6-digit code to <strong>{sessionEmail}</strong>. Enter it below to access your dashboard. If you don&apos;t see it, check your spam folder.
                </Typography>
                <TextField
                  placeholder="000000"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  fullWidth
                  size="small"
                  inputProps={{ inputMode: "numeric", maxLength: 6, "aria-label": "Verification code" }}
                  sx={{
                    mb: 2,
                    "& .MuiOutlinedInput-root": { borderRadius: 2, height: 44 },
                    "& .MuiInputBase-input": { fontSize: "1.25rem", letterSpacing: "0.25em", textAlign: "center" },
                  }}
                />
                <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
                  <Button
                    onClick={handleResendCode}
                    disabled={resendCooldown > 0 || isResending}
                    variant="text"
                    size="small"
                    sx={{ textTransform: "none", color: resendCooldown > 0 ? "text.disabled" : "#4D8AFF", p: 0, minWidth: 0 }}
                  >
                    {isResending
                      ? "Sending…"
                      : resendCooldown > 0
                      ? `Resend code in ${resendCooldown}s`
                      : "Resend code"}
                  </Button>
                </Box>
                <Button
                  onClick={handleVerifyCode}
                  disabled={verifyingCode || verificationCode.length !== 6}
                  fullWidth
                  variant="contained"
                  startIcon={verifyingCode ? <CircularProgress size={20} color="inherit" sx={{ flexShrink: 0 }} /> : undefined}
                  sx={{
                    bgcolor: "#4D8AFF",
                    "&:hover": { bgcolor: "#3D7AEF" },
                    textTransform: "none",
                    fontWeight: 600,
                    borderRadius: 2,
                    py: 1.25,
                  }}
                >
                  {verifyingCode ? "Verifying…" : "Verify and go to dashboard"}
                </Button>
              </Box>
            ) : null}

            {!needsVerificationCode && (
              <Button
                onClick={handleSubmit}
                disabled={isSubmitting || !!pendingSignIn}
                fullWidth
                variant="contained"
                startIcon={
                  (isSubmitting || pendingSignIn) ? (
                    <CircularProgress size={20} color="inherit" sx={{ flexShrink: 0 }} />
                  ) : undefined
                }
                sx={{
                  mt: { xs: 3, sm: 4 },
                  height: { xs: 44, sm: 48 },
                  bgcolor: "#4D8AFF",
                  "&:hover": { bgcolor: "#3D7AEF" },
                  "&.Mui-disabled": {
                    bgcolor: "rgba(77, 138, 255, 0.6)",
                    color: "rgba(255, 255, 255, 0.9)",
                  },
                  textTransform: "none",
                  fontWeight: 600,
                  borderRadius: 2,
                  fontSize: { xs: "0.875rem", sm: "1rem" },
                }}
              >
                {isSubmitting || pendingSignIn ? "Signing you in…" : "Create account"}
              </Button>
            )}
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

export default function AccountStep() {
  return (
    <Suspense
      fallback={
        <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "#fafafa" }}>
          <CircularProgress />
        </Box>
      }
    >
      <AccountStepContent />
    </Suspense>
  );
}
