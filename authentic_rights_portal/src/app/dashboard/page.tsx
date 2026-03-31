"use client";

import Link from "next/link";
import { ExternalLink, ArrowRight } from "lucide-react";
import { Box, Typography, Button, Card, CardContent } from "@mui/material";
import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useMemo, useRef, useState } from "react";
import { getChannels, getChannelUrlsFromResponse, getPaymentsMe, PaymentResponse } from "@/lib/api";
import { getApiToken } from "@/lib/auth";

const CONTENT_PORTAL_URL = (() => {
  const configured = process.env.NEXT_PUBLIC_CONTENT_PORTAL_URL?.trim();
  if (!configured) return "http://localhost:3002";
  return configured.replace(/\/dashboard\/?$/, "");
})();

export default function DashboardPage() {
  const { user, isLoaded } = useUser();
  const { isSignedIn, getToken } = useAuth();
  const [channelUrls, setChannelUrls] = useState<string[]>([]);
  const [paymentData, setPaymentData] = useState<PaymentResponse | null>(null);
  const [dataError, setDataError] = useState<string | null>(null);
  const [dataLoading, setDataLoading] = useState(false);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const hasAutoRefreshedRef = useRef(false);
  const displayName =
    user?.firstName ??
    user?.username ??
    user?.primaryEmailAddress?.emailAddress?.split("@")[0] ??
    "there";
  const isAdmin = (() => {
    const metadata = user?.publicMetadata as Record<string, unknown> | undefined;
    return metadata?.role === "admin" || metadata?.isAdmin === true;
  })();

  useEffect(() => {
    if (!isLoaded || !isSignedIn || isAdmin) return;
    let active = true;
    const load = async () => {
      setDataLoading(true);
      setDataError(null);
      try {
        const token = await getApiToken(getToken);
        if (!token) {
          throw new Error("Missing auth token. Please sign in again.");
        }
        const [paymentsJson, channelsJson] = await Promise.all([
          getPaymentsMe(token),
          getChannels(token),
        ]);
        if (!active) return;
        setPaymentData(paymentsJson as PaymentResponse);
        setChannelUrls(getChannelUrlsFromResponse(channelsJson));
      } catch (err) {
        if (!active) return;
        setDataError(err instanceof Error ? err.message : "Failed to load dashboard data.");
      } finally {
        if (active) setDataLoading(false);
      }
    };
    load();
    return () => {
      active = false;
    };
  }, [isLoaded, isSignedIn, getToken, isAdmin]);

  const planLabel = useMemo(() => {
    const planType = paymentData?.data?.payment?.plan_type;
    if (!planType) return "Plan details";
    return planType === "monthly" ? "Monthly" : planType === "yearly" ? "Yearly" : planType;
  }, [paymentData]);

  const nextBillingDate = useMemo(() => {
    const data = paymentData?.data;
    const raw: string | number | null | undefined =
      data?.subscription?.next_billing_date ??
      data?.renews_at ??
      data?.next_billing_date ??
      data?.current_period_end;
    if (!raw) return "Contact support";
    const timestamp = typeof raw === "number" ? raw * 1000 : raw;
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return "Contact support";
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }, [paymentData]);

  const amountLabel = useMemo(() => {
    const amount = paymentData?.data?.payment?.amount;
    const currency = paymentData?.data?.payment?.currency ?? "USD";
    if (typeof amount !== "number") return null;
    const formatted = (amount / 100).toLocaleString("en-US", {
      style: "currency",
      currency,
    });
    return formatted;
  }, [paymentData]);

  const renewalFailed = paymentData?.data?.renewal_failed === true;
  const cantoAccessSuspended = paymentData?.data?.canto_access_suspended === true;

  const renewalGraceDate = useMemo(() => {
    const raw = paymentData?.data?.renewal_grace_ends_at;
    if (!raw) return null;
    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) return null;
    return date;
  }, [paymentData]);

  useEffect(() => {
    if (!renewalFailed || !renewalGraceDate || cantoAccessSuspended) return;
    const timer = window.setInterval(() => {
      setNowMs(Date.now());
    }, 1000);
    return () => window.clearInterval(timer);
  }, [renewalFailed, renewalGraceDate, cantoAccessSuspended]);

  useEffect(() => {
    if (!renewalFailed || !renewalGraceDate || cantoAccessSuspended || hasAutoRefreshedRef.current) return;
    const graceTimeMs = renewalGraceDate.getTime();
    const key = `grace-refresh-${graceTimeMs}`;
    if (window.sessionStorage.getItem(key) === "done") return;

    const delay = graceTimeMs - Date.now();
    const reload = () => {
      hasAutoRefreshedRef.current = true;
      window.sessionStorage.setItem(key, "done");
      window.location.reload();
    };

    if (delay <= 0) {
      reload();
      return;
    }

    const timeoutId = window.setTimeout(reload, delay);
    return () => window.clearTimeout(timeoutId);
  }, [renewalFailed, renewalGraceDate, cantoAccessSuspended]);

  const renewalGraceEndsLabel = useMemo(() => {
    if (!renewalGraceDate) return null;
    return renewalGraceDate.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }, [renewalGraceDate]);

  const renewalCountdownLabel = useMemo(() => {
    if (!renewalGraceDate) return null;
    const diff = renewalGraceDate.getTime() - nowMs;
    if (diff <= 0) return "00:00:00";

    const totalSeconds = Math.floor(diff / 1000);
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    const hh = String(hours).padStart(2, "0");
    const mm = String(minutes).padStart(2, "0");
    const ss = String(seconds).padStart(2, "0");

    if (days > 0) return `${days}d ${hh}:${mm}:${ss}`;
    return `${hh}:${mm}:${ss}`;
  }, [renewalGraceDate, nowMs]);

  const actionCards = [
    {
      title: "Manage Subscription",
      description: "View and update your billing and subscription details",
      linkText: "Manage",
      href: "/dashboard/subscription",
    },
    {
      title: "Support & Help",
      description: "View frequently asked questions or contact support",
      linkText: "Get Help",
      href: "/dashboard/support",
    },
  ];

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#fafafa" }}>
      <Box
        sx={{
          pb: { xs: 3, sm: 4 },
        }}
      >
        {/* Welcome Header */}
        <Box>
          <Typography
            variant="h5"
            fontWeight="bold"
            sx={{ fontSize: { xs: "1.5rem", sm: "1.875rem" } }}
          >
            {isLoaded ? `Welcome back, ${displayName}!` : "Loading your dashboard..."}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
            Access BVIRAL&apos;s content library and manage your subscription.
          </Typography>
          {dataError ? (
            <Typography variant="body2" color="error" sx={{ mt: 1 }}>
              {dataError}
            </Typography>
          ) : null}
        </Box>

        {renewalFailed ? (
          <Box
            sx={{
              mt: { xs: 2.5, sm: 3 },
              p: { xs: 2, sm: 2.25 },
              borderRadius: 2,
              border: cantoAccessSuspended ? "1px solid #fecaca" : "1px solid #fed7aa",
              bgcolor: cantoAccessSuspended ? "#fff1f2" : "#fffbeb",
            }}
          >
            <Typography variant="subtitle2" fontWeight={700} color={cantoAccessSuspended ? "#b91c1c" : "#9a3412"}>
              {cantoAccessSuspended ? "Account Suspended" : "Payment Failed"}
            </Typography>
            <Typography variant="body2" sx={{ mt: 0.5 }} color={cantoAccessSuspended ? "#991b1b" : "#9a3412"}>
              {cantoAccessSuspended
                ? "Your account is suspended because your renewal payment failed. Please update your payment method to restore access."
                : "Your renewal payment failed. Please check your payment method to avoid service interruption."}
            </Typography>
            {renewalGraceEndsLabel && !cantoAccessSuspended ? (
              <Typography variant="body2" sx={{ mt: 1 }} color={cantoAccessSuspended ? "#991b1b" : "#9a3412"}>
                {`Your account will be suspended on ${renewalGraceEndsLabel}.`}
              </Typography>
            ) : null}
            {!cantoAccessSuspended && renewalCountdownLabel ? (
              <Box
                sx={{
                  mt: 1,
                  px: 1.25,
                  py: 0.75,
                  borderRadius: 1.5,
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 0.75,
                  bgcolor: "#ffffff",
                  border: "1px solid #fdba74",
                }}
              >
                <Typography variant="caption" sx={{ color: "#9a3412", letterSpacing: "0.04em" }}>
                  SUSPENDS IN
                </Typography>
                <Typography variant="body2" fontWeight={700} sx={{ color: "#9a3412" }}>
                  {renewalCountdownLabel}
                </Typography>
              </Box>
            ) : null}
            <Box sx={{ mt: 1.25 }}>
              <Button
                component={Link}
                href="/dashboard/subscription"
                variant="contained"
                size="small"
                sx={{
                  textTransform: "none",
                  fontWeight: 600,
                  borderRadius: "9999px",
                  bgcolor: cantoAccessSuspended ? "#b91c1c" : "#9a3412",
                  "&:hover": { bgcolor: cantoAccessSuspended ? "#991b1b" : "#7c2d12" },
                }}
              >
                Update Payment Method
              </Button>
            </Box>
          </Box>
        ) : null}

        {/* Content Library Card */}
        <Box
          sx={{
            mt: { xs: 2.5, sm: 3 },
            p: { xs: 2.5, sm: 3 },
            borderRadius: 3,
            border: "1px solid #dbeafe",
            background:
              "linear-gradient(to right, #eff6ff, rgba(239, 246, 255, 0.55))",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <Box
            sx={{
              filter: cantoAccessSuspended ? "blur(2.5px)" : "none",
              pointerEvents: cantoAccessSuspended ? "none" : "auto",
              transition: "filter 0.2s ease",
            }}
          >
            <Typography
              variant="h6"
              fontWeight="bold"
              sx={{ fontSize: { xs: "1.125rem", sm: "1.25rem" } }}
            >
              Access BVIRAL&apos;s Content Library
            </Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ mt: 1, maxWidth: "36rem" }}
            >
              Click below to access 90,000+ viral videos.
            </Typography>
            <Button
              component="a"
              href={CONTENT_PORTAL_URL}
              target="_blank"
              rel="noopener noreferrer"
              variant="contained"
              endIcon={<ExternalLink style={{ width: 16, height: 16 }} />}
              disabled={cantoAccessSuspended}
              sx={{
                mt: 1.5,
                bgcolor: "#111827",
                "&:hover": { bgcolor: "#1f2937" },
                textTransform: "none",
                fontWeight: 600,
                borderRadius: "9999px",
                px: 2.5,
              }}
            >
              Open Content Portal
            </Button>
          </Box>
          {cantoAccessSuspended ? (
            <Box
              sx={{
                position: "absolute",
                inset: 0,
                bgcolor: "rgba(255, 255, 255, 0.74)",
                backdropFilter: "blur(1.5px)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                px: 2,
              }}
            >
              <Typography variant="subtitle2" fontWeight={700} sx={{ color: "#b91c1c" }}>
                Account Suspended
              </Typography>
              <Typography variant="body2" sx={{ mt: 0.5, color: "#991b1b", maxWidth: "30rem" }}>
                Your account was suspended because payment is overdue. Please pay to restore content portal access.
              </Typography>
            </Box>
          ) : null}
        </Box>

        {/* Your Subscription Card */}
        <Card
          sx={{
            mt: 2.5,
            borderRadius: 3,
            boxShadow: "0 1px 2px rgba(15, 23, 42, 0.04)",
            border: "1px solid #e5e7eb",
            bgcolor: "#ffffff",
          }}
        >
          <CardContent sx={{ p: { xs: 2.5, sm: 3 } }}>
            <Typography variant="h6" fontWeight="bold">
              Your Subscription
            </Typography>

            <Box
              sx={{
                mt: 2.25,
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" },
                gap: { xs: 2, sm: 3 },
              }}
            >
              <Box
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  border: "1px solid #eef2f7",
                  bgcolor: "#f8fafc",
                }}
              >
                <Typography
                  variant="caption"
                  fontWeight={500}
                  color="text.secondary"
                  sx={{ textTransform: "uppercase", letterSpacing: "0.05em" }}
                >
                  Current Plan
                </Typography>
                <Typography
                  variant="body1"
                  fontWeight={600}
                  sx={{ mt: 0.5, fontSize: "1.125rem" }}
                >
                  {dataLoading ? "Loading..." : planLabel}
                </Typography>
                {amountLabel ? (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
                    {amountLabel}
                  </Typography>
                ) : null}
              </Box>
              <Box
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  border: "1px solid #eef2f7",
                  bgcolor: "#f8fafc",
                }}
              >
                <Typography
                  variant="caption"
                  fontWeight={500}
                  color="text.secondary"
                  sx={{ textTransform: "uppercase", letterSpacing: "0.05em" }}
                >
                  Active Channels
                </Typography>
                <Typography
                  variant="body1"
                  fontWeight={600}
                  sx={{ mt: 0.5, fontSize: "1.125rem" }}
                >
                  {dataLoading ? "Loading..." : channelUrls.length}
                </Typography>
              </Box>
              <Box
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  border: "1px solid #eef2f7",
                  bgcolor: "#f8fafc",
                }}
              >
                <Typography
                  variant="caption"
                  fontWeight={500}
                  color="text.secondary"
                  sx={{ textTransform: "uppercase", letterSpacing: "0.05em" }}
                >
                  Next Billing Date
                </Typography>
                <Typography
                  variant="body1"
                  fontWeight={600}
                  sx={{ mt: 0.5, fontSize: "1.125rem" }}
                >
                  {dataLoading ? "Loading..." : nextBillingDate}
                </Typography>
              </Box>
            </Box>
            <Box
              sx={{
                mt: 2.25,
                borderTop: "1px solid #e5e7eb",
                pt: 2,
                borderRadius: 2,
                bgcolor: "#fcfcfd",
                px: { xs: 1.25, sm: 1.5 },
                pb: 1.25,
              }}
            >
              <Typography
                variant="caption"
                fontWeight={500}
                color="text.secondary"
                sx={{ textTransform: "uppercase", letterSpacing: "0.05em" }}
              >
                Your Channels
              </Typography>
              {dataLoading ? (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Loading...
                </Typography>
              ) : channelUrls.length > 0 ? (
                <Box component="ul" sx={{ mt: 1, mb: 0, pl: 2.5 }}>
                  {channelUrls.map((channel, index) => (
                    <Box
                      component="li"
                      key={`${channel}-${index}`}
                      sx={{
                        color: "text.secondary",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        mb: 0.5,
                        py: 0.2,
                      }}
                    >
                      <Typography component="span" variant="body2" color="text.secondary">
                        {channel}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  No channels found.
                </Typography>
              )}
            </Box>
          </CardContent>
        </Card>

        {/* Action Cards */}
        <Box
          sx={{
            mt: 2.5,
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
            gap: { xs: 1.5, sm: 2.5 },
          }}
        >
          {actionCards.map((card) => (
            <Card
              key={card.title}
              sx={{
                borderRadius: 3,
                boxShadow: "0 1px 2px rgba(15, 23, 42, 0.04)",
                border: "1px solid #e5e7eb",
                bgcolor: "#fff",
              }}
            >
              <CardContent sx={{ p: { xs: 2.25, sm: 2.75 } }}>
                <Typography fontWeight="bold">{card.title}</Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 0.75 }}
                >
                  {card.description}
                </Typography>
                <Link
                  href={card.href}
                  style={{ textDecoration: "none" }}
                >
                  <Box
                    sx={{
                      mt: 1.5,
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 0.5,
                      color: "#111827",
                      fontWeight: 600,
                      fontSize: "0.875rem",
                      "&:hover": { color: "#6b7280" },
                      transition: "color 0.2s",
                    }}
                  >
                    {card.linkText}
                    <ArrowRight style={{ width: 16, height: 16 }} />
                  </Box>
                </Link>
              </CardContent>
            </Card>
          ))}
        </Box>
      </Box>
    </Box>
  );
}
