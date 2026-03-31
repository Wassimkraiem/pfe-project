"use client";

import { Box, Button, Card, CardContent, Typography } from "@mui/material";
import { useAuth } from "@clerk/nextjs";
import { useState } from "react";
import { CreditCard, Shield, FileText, ExternalLink } from "lucide-react";
import { getPaymentsMe } from "@/lib/api";
import { getApiToken } from "@/lib/auth";

const FEATURES = [
  { icon: CreditCard, label: "Update payment method" },
  { icon: FileText, label: "View & download invoices" },
];

export default function ManageSubscriptionPage() {
  const { isSignedIn, isLoaded, getToken } = useAuth();
  const [portalLoading, setPortalLoading] = useState(false);
  const [portalError, setPortalError] = useState<string | null>(null);

  const handleOpenBillingPortal = async () => {
    if (portalLoading) return;
    setPortalError(null);
    setPortalLoading(true);

    try {
      const token = await getApiToken(getToken);
      if (!token) throw new Error("Please sign in again.");
      const res = await getPaymentsMe(token);
      const url = res.data?.customer_portal_url ?? null;
      const portalUrl = typeof url === "string" && url.trim().length > 0 ? url.trim() : null;
      if (!portalUrl) throw new Error("Billing portal is not available for your account.");
      const portalWindow = window.open(portalUrl, "_blank", "noopener,noreferrer");

    } catch (err) {
      setPortalError(err instanceof Error ? err.message : "Failed to open billing portal.");
    } finally {
      setPortalLoading(false);
    }
  };

  if (!isLoaded) {
    return (
      <Box sx={{ py: 8, display: "flex", justifyContent: "center" }}>
        <Typography color="text.secondary">Loading...</Typography>
      </Box>
    );
  }

  if (!isSignedIn) {
    return (
      <Box sx={{ py: 8, textAlign: "center" }}>
        <Typography color="text.secondary">Please sign in to manage your subscription.</Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        maxWidth: 640,
        mr: "auto",
        ml: 0,
        py: { xs: 3, sm: 5 },
        px: { xs: 2, sm: 3 },
      }}
    >
      <Typography
        variant="h5"
        fontWeight={700}
        sx={{ mb: 0.5, fontSize: { xs: "1.25rem", sm: "1.5rem" } }}
      >
        Billing & Subscription
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
        Manage your plan and payment details in one place.
      </Typography>

      <Card
        sx={{
          borderRadius: 3,
          boxShadow: "none",
          border: "1px solid #e5e7eb",
          overflow: "hidden",
        }}
      >
        <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: 2,
              bgcolor: "rgba(77, 138, 255, 0.1)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              mb: 2,
            }}
          >
            <CreditCard style={{ width: 24, height: 24, color: "#4D8AFF" }} />
          </Box>
          <Typography variant="h6" fontWeight={600} sx={{ mb: 0.75 }}>
            Stripe Billing Portal
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Update your payment method or view invoices.
          </Typography>

          <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5, mb: 3 }}>
            {FEATURES.map(({ icon: Icon, label }) => (
              <Box
                key={label}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1.5,
                  color: "text.secondary",
                  fontSize: "0.875rem",
                }}
              >
                <Icon style={{ width: 18, height: 18, flexShrink: 0 }} />
                <span>{label}</span>
              </Box>
            ))}
          </Box>

          {portalError && (
            <Typography color="error" variant="body2" sx={{ mb: 2 }}>
              {portalError}
            </Typography>
          )}

          <Button
            variant="contained"
            fullWidth
            onClick={handleOpenBillingPortal}
            disabled={portalLoading}
            endIcon={<ExternalLink style={{ width: 16, height: 16 }} />}
            sx={{
              bgcolor: "#1E272E",
              color: "#fff",
              "&:hover": { bgcolor: "#2d3843" },
              "&.Mui-disabled": { bgcolor: "#1E272E", color: "rgba(255,255,255,0.6)" },
              textTransform: "none",
              fontWeight: 600,
              py: 1.5,
              borderRadius: 2,
              boxShadow: "0 1px 3px rgba(0,0,0,0.12)",
            }}
          >
            {portalLoading ? "Opening..." : "Open Billing Portal"}
          </Button>
        </CardContent>

        <Box
          sx={{
            px: { xs: 3, sm: 4 },
            py: 1.5,
            bgcolor: "rgba(0,0,0,0.02)",
            borderTop: "1px solid rgba(0,0,0,0.06)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 0.75,
          }}
        >
          <Shield style={{ width: 16, height: 16, color: "#6b7280" }} />
          <Typography variant="caption" color="text.secondary">
            Secure billing by Stripe
          </Typography>
        </Box>
      </Card>
    </Box>
  );
}
