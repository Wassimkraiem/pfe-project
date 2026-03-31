"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Box, CircularProgress, Typography } from "@mui/material";

const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function StripeReturnPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const onboardingSession = searchParams.get("onboarding_session")?.trim() ?? "";
    const fallbackSession = searchParams.get("session_id")?.trim() ?? "";
    const candidate = onboardingSession || fallbackSession;

    // Accept only onboarding UUIDs here; never forward Stripe checkout session IDs.
    if (candidate && UUID_REGEX.test(candidate)) {
      router.replace(`/signup/account?session_id=${encodeURIComponent(candidate)}`);
      return;
    }

    router.replace("/signup");
  }, [router, searchParams]);

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "white" }}>
      <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1.5 }}>
        <CircularProgress size={24} />
        <Typography variant="body2" color="text.secondary">
          Finalizing your payment...
        </Typography>
      </Box>
    </Box>
  );
}

export default function StripeReturnPage() {
  return (
    <Suspense
      fallback={
        <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "white" }}>
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1.5 }}>
            <CircularProgress size={24} />
            <Typography variant="body2" color="text.secondary">
              Finalizing your payment...
            </Typography>
          </Box>
        </Box>
      }
    >
      <StripeReturnPageContent />
    </Suspense>
  );
}
