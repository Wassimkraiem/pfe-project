"use client";

import { useState, useEffect, Suspense, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { keyframes } from "@emotion/react";
import { Caveat } from "next/font/google";
import { Check, ChevronDown } from "lucide-react";
import { loadStripe } from "@stripe/stripe-js";
import { EmbeddedCheckout, EmbeddedCheckoutProvider } from "@stripe/react-stripe-js";
import StepIndicator from "@/components/StepIndicator";
import { useBeforeUnload } from "@/hooks/useBeforeUnload";
import {
  createCheckout,
  getOnboardingSessionByEmail,
  getOnboardingSessionChannelUrls,
  getOnboardingSessionChannelsCount,
  getPaymentPrice,
  PaymentPriceData,
} from "@/lib/api";
import { LICENSING_AGREEMENT } from "@/lib/licensingAgreement";
import { Box, Typography, Button, TextField, Dialog, IconButton, CircularProgress, Checkbox } from "@mui/material";
import { X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const arrowBounceKeyframes = keyframes`
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(5px); }
`;

const signatureFont = Caveat({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const steps = [
  { number: 1, label: "Email" },
  { number: 2, label: "Pages" },
  { number: 3, label: "Checkout" },
  { number: 4, label: "Account" },
];

const STRIPE_PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;
const stripePromise = STRIPE_PUBLISHABLE_KEY ? loadStripe(STRIPE_PUBLISHABLE_KEY) : null;

const PRICE_PER_CHANNEL = 399;

const INCLUDED = [
  "Unlimited, watermark-free downloads",
  "Access to 90k+ videos",
  "New videos added weekly",
  "Cleared for Monetization",
  "Full editing permissions",
];


function normalizePrice(
  price: PaymentPriceData | null
): { amount: number; plan: "monthly" | "yearly" } | null {
  if (!price) return null;
  const amount = typeof price.price === "number" ? price.price : null;
  if (amount === null || !Number.isFinite(amount)) return null;
  const plan: "monthly" | "yearly" = price.plan === "yearly" ? "yearly" : "monthly";
  return { amount, plan };
}

function CheckoutStepContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const email = searchParams.get("email") ?? "";
  const channelsParam = searchParams.get("channels");
  const priceId = searchParams.get("price_id") ?? "";
  const [channelsCount, setChannelsCount] = useState<number>(() => {
    const parsed = parseInt(channelsParam ?? "", 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
  });
  const [channelUrls, setChannelUrls] = useState<string[]>([]);
  const formatAmount = (n: number) => n.toLocaleString();
  const formatCurrency = (amount: number) => `$${formatAmount(amount)}`;

  const [plan, setPlan] = useState<"monthly" | "yearly">("monthly");
  const [signature, setSignature] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [priceLoading, setPriceLoading] = useState(false);
  const [lockedPrice, setLockedPrice] = useState<{
    amount: number;
    plan: "monthly" | "yearly";
  } | null>(null);
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [checkoutUrl, setCheckoutUrl] = useState<string | null>(null);
  const [overlayOpen, setOverlayOpen] = useState(false);
  const [channelsLoading, setChannelsLoading] = useState(true);
  const [agreementModalOpen, setAgreementModalOpen] = useState(false);
  const [agreementScrolledToEnd, setAgreementScrolledToEnd] = useState(false);
  const [agreementAccepted, setAgreementAccepted] = useState(false);
  const [serviceAgreementSignedAt, setServiceAgreementSignedAt] = useState<string | null>(null);
  const [paymentComplete, setPaymentComplete] = useState(false);
  const agreementScrollRef = useRef<HTMLDivElement>(null);
  const currentStep = 3;

  const disableBeforeUnload = useBeforeUnload(!paymentComplete && !overlayOpen);

  const handleAgreementScroll = useCallback(() => {
    const el = agreementScrollRef.current;
    if (!el) return;
    const { scrollTop, scrollHeight, clientHeight } = el;
    const atEnd = scrollHeight - scrollTop - clientHeight < 24;
    setAgreementScrolledToEnd(atEnd);
  }, []);

  const scrollAgreementToEnd = useCallback(() => {
    agreementScrollRef.current?.scrollTo({ top: agreementScrollRef.current.scrollHeight, behavior: "smooth" });
  }, []);

  useEffect(() => {
    if (!agreementModalOpen) return;
    const t = setTimeout(() => handleAgreementScroll(), 100);
    return () => clearTimeout(t);
  }, [agreementModalOpen, handleAgreementScroll]);

  const planLocked = lockedPrice !== null;
  const priceReady = !priceLoading;

  // Plan-based totals: monthly = per month; yearly = pay 10 months upfront (2 months free)
  const totalPerMonth = channelsCount * PRICE_PER_CHANNEL;
  const yearlyListPrice = totalPerMonth * 12;
  const upfrontTotal = totalPerMonth * 10;
  const yearlyDiscount = yearlyListPrice - upfrontTotal;
  const total = lockedPrice ? lockedPrice.amount : plan === "monthly" ? totalPerMonth : upfrontTotal;

  useEffect(() => {
    if (!email.trim()) {
      router.replace("/signup");
    }
  }, [email, router]);

  useEffect(() => {
    if (!email.trim()) return;
    let active = true;
    setChannelsLoading(true);
    getOnboardingSessionByEmail(email)
      .then((res) => {
        if (!active) return;
        const urls = getOnboardingSessionChannelUrls(res.data);
        if (urls.length > 0) {
          setChannelUrls(urls);
          setChannelsCount(urls.length);
          return;
        }
        const count = getOnboardingSessionChannelsCount(res.data);
        if (count && count > 0) setChannelsCount(count);
      })
      .catch(() => {
        if (active) setChannelUrls([]);
      })
      .finally(() => {
        if (active) setChannelsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [email, channelsParam]);

  const handleCompletePayment = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (loading || overlayOpen || priceLoading) return;
    setError(null);
    if (!agreementAccepted) {
      setError("Please read and agree to the Licensing Agreement first.");
      return;
    }
    if (!signature.trim()) {
      setError("Please enter your full name to agree to the terms.");
      return;
    }
    if (!serviceAgreementSignedAt) {
      setError("Please sign the Licensing Agreement to continue.");
      return;
    }
    if (!STRIPE_PUBLISHABLE_KEY || !stripePromise) {
      setError("Stripe is not configured. Please set NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY.");
      return;
    }
    setLoading(true);
    try {
      const res = await createCheckout(
        email,
        plan,
        "subscription",
        signature,
        serviceAgreementSignedAt
      );
      const url = res.data?.checkout_url?.trim();
      const nextClientSecret = res.data?.client_secret?.trim();
      if (nextClientSecret) {
        setClientSecret(nextClientSecret);
        setCheckoutUrl(null);
        setOverlayOpen(true);
      } else if (url) {
        setCheckoutUrl(url);
        setClientSecret(null);
        setOverlayOpen(true);
      } else {
        setError(res.message?.trim() || "Something went wrong. Please try again.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!priceId.trim()) {
      setLockedPrice(null);
      return;
    }
    let active = true;
    setPriceLoading(true);
    getPaymentPrice(priceId)
      .then((res) => {
        if (!active) return;
        const normalized = normalizePrice(res.data ?? null);
        setLockedPrice(normalized);
        if (normalized) setPlan(normalized.plan);
      })
      .catch(() => {
        if (active) setLockedPrice(null);
      })
      .finally(() => {
        if (active) setPriceLoading(false);
      });
    return () => {
      active = false;
    };
  }, [priceId]);

  if (!email.trim()) {
    return null;
  }

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "white", overflowX: "hidden" }}>
      <Box
        sx={{
          maxWidth: "56rem",
          mx: "auto",
          px: { xs: 2, sm: 3, lg: 4 },
          py: { xs: 3, sm: 4 },
          pb: { xs: "max(24px, env(safe-area-inset-bottom))", sm: undefined },
          minWidth: 0,
        }}
      >
        <Box sx={{ maxWidth: "42rem", mx: "auto" }}>
          <StepIndicator steps={steps} currentStep={currentStep} />
        </Box>

        <Box
          sx={{
            mx: "auto",
            mt: 3,
            maxWidth: "42rem",
            borderTop: "1px solid #e5e7eb",
          }}
        />

        {/* Two-column: Order Summary (left) + Billing/Agreement (right) */}
        <Box
          sx={{
            mx: "auto",
            mt: { xs: 4, sm: 6 },
            maxWidth: "56rem",
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
            gap: { xs: 3, md: 4 },
            minWidth: 0,
          }}
        >
          {/* Left: Order Summary */}
          <Box
            sx={{
              p: { xs: 2, sm: 3 },
              borderRadius: 3,
              border: "1px solid #e5e7eb",
              height: "fit-content",
              minWidth: 0,
              overflow: "hidden",
            }}
          >
            <Typography variant="body2" color="text.primary">
              {plan === "yearly" ? "Due today" : "Total Amount"}
            </Typography>
            {plan === "yearly" && !lockedPrice ? (
              <Box sx={{ mt: 0.5 }}>
                <Typography
                  component="span"
                  sx={{
                    display: "block",
                    fontSize: "1.125rem",
                    color: "text.secondary",
                    textDecoration: "line-through",
                    textDecorationThickness: "2px",
                  }}
                >
                  {formatCurrency(yearlyListPrice)}
                </Typography>
                <Typography variant="h4" fontWeight="bold" sx={{ color: "#22a35a", lineHeight: 1.15 }}>
                  {formatCurrency(upfrontTotal)}
                </Typography>
              </Box>
            ) : (
              <Typography variant="h4" fontWeight="bold" sx={{ mt: 0.5 }}>
                {formatCurrency(total)}
              </Typography>
            )}
            <Typography variant="body2" color="text.primary" sx={{ fontSize: "0.875rem" }}>
              {lockedPrice
                ? lockedPrice.plan === "yearly"
                  ? "per year"
                  : "per month"
                : plan === "monthly"
                ? "per month"
                : "billed yearly"}
            </Typography>
            {plan === "yearly" && !lockedPrice && (
              <Typography variant="body2" sx={{ mt: 0.5, fontSize: "0.8125rem", color: "#16a34a", fontWeight: 600 }}>
                Save {formatCurrency(yearlyDiscount)} with annual billing (2 months free)
              </Typography>
            )}

            <Box sx={{ borderTop: "1px solid #e5e7eb", mt: 2, pt: 2 }}>
              <Typography fontWeight={600} sx={{ mb: 1 }} fontSize="0.875rem">
                What&apos;s Included
              </Typography>
              <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
                {INCLUDED.map((item) => (
                  <Box
                    component="li"
                    key={item}
                    sx={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 1,
                      mb: 0.75,
                      listStyle: "none",
                      "&::before": { content: "none" },
                    }}
                  >
                    <Check style={{ width: 18, height: 18, color: "#22c55e", flexShrink: 0, marginTop: 2 }} />
                    <Typography variant="body2">{item}</Typography>
                  </Box>
                ))}
              </Box>
            </Box>

            <Box sx={{ borderTop: "1px solid #e5e7eb", mt: 2, pt: 2 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 1, minWidth: 0 }}>
                <Typography variant="body2" sx={{ minWidth: 0, flexShrink: 1 }}>
                  {channelUrls.length || channelsCount} Channel{(channelUrls.length || channelsCount) !== 1 ? "s" : ""}{!lockedPrice && ` × $${formatAmount(PRICE_PER_CHANNEL)}/mo`}
                </Typography>
                <Typography variant="body2" fontWeight={500} sx={{ flexShrink: 0 }}>
                  {lockedPrice
                    ? formatCurrency(total)
                    : plan === "monthly"
                    ? `$${formatAmount(totalPerMonth)}/mo`
                    : `$${formatAmount(upfrontTotal)} due today`}
                </Typography>
              </Box>
              {channelUrls.length > 0 && (
                <Box sx={{ mt: 1 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                    Channels in this subscription
                  </Typography>
                  <Box component="ul" sx={{ m: 0, pl: 2 }}>
                    {channelUrls.map((url, index) => (
                      <Box
                        component="li"
                        key={`${url}-${index}`}
                        sx={{
                          listStyle: "disc",
                          color: "text.secondary",
                          wordBreak: "break-all",
                        }}
                      >
                        <Typography component="span" variant="caption" color="text.secondary">
                          {url}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}
              <Box sx={{ mt: 1.5, display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 1, minWidth: 0 }}>
                <Typography fontWeight={600} fontSize="0.875rem" sx={{ flexShrink: 0 }}>
                  {plan === "yearly" ? "Total due today" : "Total due"}
                </Typography>
                <Box sx={{ textAlign: "right", minWidth: 0 }}>
                  <Typography fontWeight="bold" sx={{ fontSize: { xs: "1rem", sm: "1.125rem" } }}>
                    {formatCurrency(total)}
                  </Typography>
                  <Typography variant="body2" sx={{ display: "block", fontSize: "0.8125rem", wordBreak: "break-word" }}>
                    {lockedPrice
                      ? lockedPrice.plan === "yearly"
                        ? "per year"
                        : "per month"
                      : plan === "monthly"
                      ? "per month"
                      : `($${formatAmount(totalPerMonth)}/mo equivalent)`}
                  </Typography>
                </Box>
              </Box>
            </Box>
          </Box>

          {/* Right: Billing & Agreement (card matching left) */}
          <Box
            sx={{
              p: { xs: 2, sm: 3 },
              borderRadius: 3,
              border: "1px solid #e5e7eb",
              height: "fit-content",
              minWidth: 0,
              overflow: "visible",
            }}
          >
            <Typography fontWeight={600} fontSize="0.875rem" sx={{ mb: 1 }}>
              Billing Period
            </Typography>
            {planLocked ? (
              <Box
                sx={{
                  mb: 3,
                  p: 2,
                  borderRadius: 2,
                  bgcolor: "#4D8AFF",
                  color: "#fff",
                  textAlign: "center",
                }}
              >
                <Typography sx={{ fontSize: "1rem", fontWeight: 700, color: "inherit" }}>
                  {plan === "monthly" ? "Pay Monthly" : "Pay Annually"}
                </Typography>
                {plan === "monthly" && (
                  <Typography sx={{ fontSize: "0.8125rem", fontWeight: 500, opacity: 0.9, mt: 0.25, color: "inherit" }}>
                    (1-Year Contract)
                  </Typography>
                )}
              </Box>
            ) : (
              <Box
                sx={{
                  display: "flex",
                  flexDirection: { xs: "column", sm: "row" },
                  gap: 1,
                  mb: 3,
                }}
              >
                <Button
                  variant={plan === "monthly" ? "contained" : "outlined"}
                  onClick={() => setPlan("monthly")}
                  sx={{
                    flex: 1,
                    minWidth: 0,
                    textTransform: "none",
                    fontWeight: 600,
                    borderRadius: 2,
                    py: 1.5,
                    flexDirection: "column",
                    ...(plan === "monthly" && { bgcolor: "#4D8AFF", "&:hover": { bgcolor: "#3D7AEF" } }),
                  }}
                >
                  <Box sx={{ display: "block", lineHeight: 1.3, color: "inherit" }}>
                    <Typography component="span" sx={{ display: "block", fontSize: { xs: "0.875rem", sm: "0.9375rem" }, color: "inherit" }}>
                      Pay Monthly
                    </Typography>
                    <Typography component="span" sx={{ display: "block", fontSize: "0.75rem", fontWeight: 500, opacity: 0.95, color: "inherit" }}>
                      (1-Year Contract)
                    </Typography>
                  </Box>
                </Button>
                <Button
                  variant={plan === "yearly" ? "contained" : "outlined"}
                  onClick={() => setPlan("yearly")}
                  sx={{
                    flex: 1,
                    minWidth: 0,
                    textTransform: "none",
                    fontWeight: 600,
                    borderRadius: 2,
                    py: 1.5,
                    flexDirection: "column",
                    ...(plan === "yearly" && { bgcolor: "#4D8AFF", "&:hover": { bgcolor: "#3D7AEF" } }),
                  }}
                >
                  <Box sx={{ display: "block", lineHeight: 1.3, color: "inherit" }}>
                    <Typography component="span" sx={{ display: "block", fontSize: { xs: "0.875rem", sm: "0.9375rem" }, color: "inherit" }}>
                      Pay Annually
                    </Typography>
                    <Typography component="span" sx={{ display: "block", fontSize: "0.75rem", fontWeight: 500, opacity: 0.95, color: "inherit" }}>
                      (Get 2 months free!)
                    </Typography>
                  </Box>
                </Button>
              </Box>
            )}

            <Box>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: 0.75,
                  mb: 2,
                  minWidth: 0,
                }}
              >
                <Checkbox
                  checked={agreementAccepted}
                  onClick={(e) => {
                    if (agreementAccepted) {
                      setAgreementAccepted(false);
                      setServiceAgreementSignedAt(null);
                    } else {
                      e.preventDefault();
                      setAgreementModalOpen(true);
                      setAgreementScrolledToEnd(false);
                    }
                  }}
                  sx={{
                    p: 0.25,
                    flexShrink: 0,
                    "& .MuiSvgIcon-root": { fontSize: 20 },
                  }}
                />
                <Typography
                  variant="body2"
                  component="span"
                  sx={{
                    lineHeight: 1.5,
                    textAlign: "left",
                    flex: "1 1 0%",
                    minWidth: 0,
                    whiteSpace: "normal",
                    wordBreak: "break-word",
                    overflowWrap: "break-word",
                    py: 0.25,
                  }}
                >
                  I am at least 18 years of age and have read and fully agree to the{" "}
                  <Box
                    component="span"
                    onClick={(e) => {
                      e.preventDefault();
                      setAgreementModalOpen(true);
                      setAgreementScrolledToEnd(false);
                    }}
                    sx={{
                      color: "#4D8AFF",
                      textDecoration: "underline",
                      cursor: "pointer",
                      "&:hover": { color: "#3D7AEF" },
                    }}
                  >
                    Licensing Agreement
                  </Box>
                  .
                </Typography>
              </Box>

              {signature.trim() && (
                <Box sx={{ mb: 2 }}>
                  <Typography fontWeight={600} fontSize="0.875rem" sx={{ mb: 0.5 }}>
                    Digital Signature
                  </Typography>
                  <Box
                    className={signatureFont.className}
                    sx={{
                      px: 2,
                      py: 1,
                      borderRadius: 2,
                      border: "1px solid #e5e7eb",
                      bgcolor: "rgba(0,0,0,0.02)",
                    }}
                  >
                    <Typography
                      sx={{
                        fontFamily: signatureFont.style.fontFamily,
                        fontSize: "1.125rem",
                        color: "#111827",
                      }}
                    >
                      {signature}
                    </Typography>
                  </Box>
                </Box>
              )}
            </Box>

            {error && (
              <Typography color="error" fontSize="0.875rem" sx={{ mb: 1 }}>
                {error}
              </Typography>
            )}
            {priceLoading && (
              <Typography color="text.secondary" fontSize="0.875rem" sx={{ mb: 1 }}>
                Loading price…
              </Typography>
            )}

            <Typography
              component="p"
              sx={{
                mb: 2,
                fontStyle: "italic",
                fontSize: "0.75rem",
                color: "text.secondary",
                lineHeight: 1.5,
                wordBreak: "break-word",
                overflowWrap: "break-word",
              }}
            >
              *1-year commitment required. Your subscription auto-renews annually unless cancelled with 30 days&apos; notice.
            </Typography>

            <Box
              sx={{
                display: "flex",
                flexDirection: { xs: "column-reverse", sm: "row" },
                gap: 1.5,
              }}
            >
              <Button
                component={Link}
                href={`/signup/pages?email=${encodeURIComponent(email)}`}
                fullWidth
                variant="outlined"
                sx={{
                  minHeight: { xs: 48, sm: 48 },
                  py: { xs: 1.5, sm: 1 },
                  textTransform: "none",
                  fontWeight: 600,
                  borderRadius: 2,
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
                disabled={loading || overlayOpen || !priceReady || !agreementAccepted}
                onClick={handleCompletePayment}
                startIcon={
                  loading ? (
                    <CircularProgress size={20} color="inherit" sx={{ flexShrink: 0 }} />
                  ) : undefined
                }
                sx={{
                  minHeight: { xs: 48, sm: 48 },
                  py: { xs: 1.5, sm: 1 },
                  bgcolor: "#4D8AFF",
                  "&:hover": { bgcolor: "#3D7AEF" },
                  textTransform: "none",
                  fontWeight: 600,
                  borderRadius: 2,
                }}
              >
                {loading
                  ? "Opening…"
                  : lockedPrice
                  ? `Pay ${formatCurrency(total)}`
                  : plan === "monthly"
                  ? `Pay $${formatAmount(totalPerMonth)}/month`
                  : `Pay $${formatAmount(upfrontTotal)} annually`}
              </Button>
            </Box>

            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2, textAlign: "center" }}>
              By submitting your payment, you authorize BVIRAL to charge your card for this subscription and future renewals.
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Service Agreement modal */}
      <Dialog
        open={agreementModalOpen}
        onClose={() => setAgreementModalOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 2,
            maxHeight: "90vh",
            overflow: "hidden",
          },
        }}
      >
        <Box sx={{ display: "flex", flexDirection: "column", maxHeight: "90vh" }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              px: 2,
              py: 1.5,
              borderBottom: "1px solid #e5e7eb",
            }}
          >
            <Typography variant="h6" fontWeight={600}>
              Licensing Agreement
            </Typography>
            <IconButton
              onClick={() => setAgreementModalOpen(false)}
              aria-label="Close"
              sx={{ color: "text.secondary" }}
            >
              <X style={{ width: 20, height: 20 }} />
            </IconButton>
          </Box>
          <Box
            ref={agreementScrollRef}
            onScroll={handleAgreementScroll}
            sx={{
              flex: 1,
              overflow: "auto",
              px: 2,
              py: 2,
              minHeight: 200,
              maxHeight: 420,
            }}
          >
            <Box
              sx={{
                "& h1, & h2, & h3, & h4, & h5, & h6": {
                  fontWeight: 700,
                  mt: 2,
                  mb: 1,
                },
                "& p": {
                  fontSize: "0.875rem",
                  lineHeight: 1.6,
                  mb: 1.5,
                },
                "& strong": {
                  fontWeight: 700,
                },
                "& table": {
                  width: "100%",
                  borderCollapse: "collapse",
                  mb: 2,
                  fontSize: "0.8125rem",
                },
                "& th, & td": {
                  border: "1px solid #e5e7eb",
                  p: 1,
                  textAlign: "left",
                  verticalAlign: "top",
                },
                "& th": {
                  fontWeight: 700,
                  bgcolor: "#f9fafb",
                },
                "& hr": {
                  my: 2,
                  border: "none",
                  borderTop: "1px solid #e5e7eb",
                },
                "& a": {
                  color: "#4D8AFF",
                  textDecoration: "underline",
                },
                "& img": {
                  maxWidth: 180,
                  height: "auto",
                  my: 1,
                },
                "& ul, & ol": {
                  pl: 2,
                  mb: 1.5,
                },
                "& li": {
                  fontSize: "0.875rem",
                  mb: 0.5,
                },
              }}
            >
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  img: ({ src, alt, ...props }) =>
                    src ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={src} alt={alt ?? ""} {...props} />
                    ) : null,
                }}
              >
                {LICENSING_AGREEMENT}
              </ReactMarkdown>
            </Box>

            {/* Signature field at end of scrollable content */}
            <Box
              sx={{
                mt: 3,
                pt: 2,
                borderTop: "1px solid #e5e7eb",
              }}
            >
              <Typography fontWeight={600} fontSize="0.875rem" sx={{ mb: 1 }}>
                Digital Signature <Typography component="span" color="error">*</Typography>
              </Typography>
              <Box className={signatureFont.className}>
                <TextField
                  placeholder="Type your full name to sign"
                  value={signature}
                  onChange={(e) => setSignature(e.target.value)}
                  fullWidth
                  size="small"
                  sx={{
                    mb: 0.5,
                    "& .MuiOutlinedInput-root": { borderRadius: 2 },
                    "& .MuiInputBase-input": {
                      fontFamily: signatureFont.style.fontFamily,
                      fontSize: "1.125rem",
                    },
                  }}
                />
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                By typing your name, you agree to the terms above and authorize payment.
              </Typography>
            </Box>
          </Box>
          {!agreementScrolledToEnd && (
            <Box
              sx={{
                display: "flex",
                justifyContent: "center",
                py: 2,
                px: 2,
                borderTop: "1px solid #e5e7eb",
                bgcolor: "#fff",
                flexShrink: 0,
              }}
            >
              <Button
                variant="contained"
                onClick={scrollAgreementToEnd}
                startIcon={
                  <Box
                    component="span"
                    sx={{
                      display: "inline-flex",
                      animation: `${arrowBounceKeyframes} 1.8s ease-in-out infinite`,
                    }}
                  >
                    <ChevronDown style={{ width: 18, height: 18 }} />
                  </Box>
                }
                sx={{
                  bgcolor: "#E3F2FD",
                  color: "#1565C0",
                  "&:hover": { bgcolor: "#BBDEFB", color: "#0D47A1" },
                  textTransform: "none",
                  fontWeight: 600,
                  borderRadius: 2,
                  py: 1.25,
                  px: 2,
                }}
              >
                Scroll down to sign the agreement
              </Button>
            </Box>
          )}
          <Box sx={{ p: 2, borderTop: "1px solid #e5e7eb" }}>
            <Button
              fullWidth
              variant="contained"
              disabled={!agreementScrolledToEnd || !signature.trim()}
              onClick={() => {
                setAgreementAccepted(true);
                setServiceAgreementSignedAt(new Date().toISOString());
                setAgreementModalOpen(false);
              }}
              sx={{
                bgcolor: agreementScrolledToEnd && signature.trim() ? "#4D8AFF" : "#e5e7eb",
                color: agreementScrolledToEnd && signature.trim() ? "#fff" : "#9ca3af",
                "&:hover": agreementScrolledToEnd && signature.trim() ? { bgcolor: "#3D7AEF" } : {},
                "&.Mui-disabled": { bgcolor: "#e5e7eb", color: "#9ca3af" },
                textTransform: "none",
                fontWeight: 600,
                py: 1.5,
                borderRadius: 2,
              }}
            >
              I Read & Agree to Licensing Agreement
            </Button>
          </Box>
        </Box>
      </Dialog>

      {/* Stripe Embedded Checkout modal */}
      <Dialog
        open={overlayOpen}
        onClose={() => {
          setOverlayOpen(false);
          setCheckoutUrl(null);
          setClientSecret(null);
        }}
        maxWidth={false}
        fullWidth
        disableScrollLock
        transitionDuration={300}
        PaperProps={{
          sx: {
            maxWidth: { xs: "100%", sm: 640 },
            width: "100%",
            height: { xs: "100%", sm: "90vh" },
            maxHeight: "90vh",
            borderRadius: { xs: 0, sm: 2 },
            overflow: "hidden",
          },
        }}
        sx={{ "& .MuiDialog-container": { alignItems: { xs: "stretch", sm: "center" } } }}
      >
        <Box sx={{ position: "relative", height: "100%", display: "flex", flexDirection: "column", minHeight: 0 }}>
          <Box
            sx={{
              position: "absolute",
              top: 8,
              right: 8,
              zIndex: 2,
              display: "flex",
              alignItems: "center",
            }}
          >
            <IconButton
              size="small"
              onClick={() => setOverlayOpen(false)}
              sx={{ bgcolor: "rgba(0,0,0,0.04)", "&:hover": { bgcolor: "rgba(0,0,0,0.08)" } }}
              aria-label="Close"
            >
              <X style={{ width: 20, height: 20 }} />
            </IconButton>
          </Box>
          {clientSecret && stripePromise ? (
            <Box sx={{ flex: 1, width: "100%", mt: 5, minHeight: 480, overflow: "auto" }}>
              <EmbeddedCheckoutProvider
                stripe={stripePromise}
                options={{
                  clientSecret,
                  onComplete: () => {
                    disableBeforeUnload();
                    setPaymentComplete(true);
                  },
                }}
              >
                <EmbeddedCheckout />
              </EmbeddedCheckoutProvider>
            </Box>
          ) : (
            <Box
              sx={{
                flex: 1,
                width: "100%",
                minHeight: 480,
                mt: 5,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Typography variant="body2" color="text.secondary">
                Loading checkout…
              </Typography>
            </Box>
          )}
          {checkoutUrl && !clientSecret && (
            <Box
              component="iframe"
              key={checkoutUrl}
              src={checkoutUrl}
              title="Lemon Squeezy Checkout"
              sx={{
                flex: 1,
                width: "100%",
                minHeight: 480,
                border: "none",
                mt: 5,
              }}
            />
          )}
        </Box>
      </Dialog>
    </Box>
  );
}

export default function CheckoutStep() {
  return (
    <Suspense
      fallback={
        <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "#fafafa" }}>
          <CircularProgress />
        </Box>
      }
    >
      <CheckoutStepContent />
    </Suspense>
  );
}
