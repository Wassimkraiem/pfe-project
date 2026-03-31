"use client";

import {
  DollarSign,
  Users,
  TrendingUp,
  CheckCircle,
  ExternalLink,
} from "lucide-react";
import { Box, Typography, Button, Card, CardContent } from "@mui/material";

const features = [
  {
    icon: DollarSign,
    title: "20% Commission",
    description: "Earn recurring commissions on every subscription you refer",
  },
  {
    icon: Users,
    title: "Easy Tracking",
    description:
      "Monitor your referrals and earnings in our affiliate dashboard",
  },
  {
    icon: TrendingUp,
    title: "No Limits",
    description: "Unlimited earning potential with no caps on commissions",
  },
];

const benefits = [
  "Earn 20% recurring commission on every referral",
  "Access exclusive promotional materials and resources",
  "No limit on how much you can earn",
  "Get paid monthly with a $100 minimum payout threshold",
  "Track your referrals and earnings in real-time",
  "Lifetime cookie tracking for your referrals",
];

const howItWorks = [
  {
    step: 1,
    title: "Join the Program",
    description: "Sign up for free through our affiliate platform",
  },
  {
    step: 2,
    title: "Share Your Link",
    description: "Promote BVIRAL using your unique affiliate link",
  },
  {
    step: 3,
    title: "Earn Commissions",
    description: "Get paid monthly for every successful referral",
  },
];

export default function AffiliatePage() {
  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#fafafa" }}>
      <Box sx={{ px: { xs: 2, sm: 3, lg: 4 }, py: { xs: 4, sm: 6 } }}>
        {/* Header */}
        <Box>
          <Typography
            variant="h5"
            fontWeight="bold"
            sx={{ fontSize: { xs: "1.5rem", sm: "1.875rem" } }}
          >
            Become an Affiliate
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
            Earn commissions by referring customers to BVIRAL
          </Typography>
        </Box>

        {/* Join Program Card - Green Gradient */}
        <Box
          sx={{
            mt: 4,
            p: { xs: 3, sm: 4 },
            borderRadius: 3,
            background:
              "linear-gradient(to right, #f0fdf4, rgba(240, 253, 244, 0.5))",
          }}
        >
          <Typography
            variant="h6"
            fontWeight="bold"
            sx={{ fontSize: { xs: "1.25rem", sm: "1.5rem" } }}
          >
            Join the BVIRAL Affiliate Program
          </Typography>
          <Typography
            variant="body1"
            color="text.secondary"
            sx={{ mt: 1.5, maxWidth: "42rem" }}
          >
            Share BVIRAL with your audience and earn generous commissions on
            every subscription. Our affiliate program is designed to reward you
            for helping creators and brands access high-quality viral content.
          </Typography>
          <Button
            variant="contained"
            endIcon={<ExternalLink style={{ width: 16, height: 16 }} />}
            sx={{
              mt: 3,
              bgcolor: "#111827",
              "&:hover": { bgcolor: "#1f2937" },
              textTransform: "none",
              fontWeight: 600,
              borderRadius: "9999px",
            }}
          >
            Join Affiliate Program
          </Button>
        </Box>

        {/* Feature Cards */}
        <Box
          sx={{
            mt: 3,
            display: "grid",
            gap: 2,
            gridTemplateColumns: { sm: "repeat(2, 1fr)", lg: "repeat(3, 1fr)" },
          }}
        >
          {features.map((feature) => (
            <Card
              key={feature.title}
              sx={{
                borderRadius: 3,
                boxShadow: "none",
                border: "1px solid #e5e7eb",
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: 40,
                    height: 40,
                    borderRadius: 2,
                    border: "1px solid #e5e7eb",
                  }}
                >
                  <feature.icon style={{ width: 20, height: 20 }} />
                </Box>
                <Typography variant="h6" fontWeight="bold" sx={{ mt: 2 }}>
                  {feature.title}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 1 }}
                >
                  {feature.description}
                </Typography>
              </CardContent>
            </Card>
          ))}
        </Box>

        {/* What You Get Card */}
        <Card
          sx={{
            mt: 3,
            borderRadius: 3,
            boxShadow: "none",
            border: "1px solid #e5e7eb",
          }}
        >
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight="bold">
              What You Get as a BVIRAL Affiliate
            </Typography>

            <Box
              sx={{
                mt: 3,
                display: "grid",
                gap: 2,
                gridTemplateColumns: { sm: "repeat(2, 1fr)" },
              }}
            >
              {benefits.map((benefit, index) => (
                <Box
                  key={index}
                  sx={{ display: "flex", alignItems: "flex-start", gap: 1.5 }}
                >
                  <CheckCircle
                    style={{
                      width: 20,
                      height: 20,
                      flexShrink: 0,
                      marginTop: 2,
                      color: "#9ca3af",
                    }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    {benefit}
                  </Typography>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>

        {/* How It Works Card */}
        <Card
          sx={{
            mt: 3,
            borderRadius: 3,
            boxShadow: "none",
            border: "1px solid #e5e7eb",
          }}
        >
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight="bold">
              How It Works
            </Typography>

            <Box
              sx={{
                mt: 4,
                display: "grid",
                gap: 4,
                gridTemplateColumns: { sm: "repeat(3, 1fr)" },
              }}
            >
              {howItWorks.map((item) => (
                <Box key={item.step} sx={{ textAlign: "center" }}>
                  <Box
                    sx={{
                      mx: "auto",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: 40,
                      height: 40,
                      borderRadius: "50%",
                      bgcolor: "#111827",
                      color: "white",
                      fontWeight: "bold",
                      fontSize: "0.875rem",
                    }}
                  >
                    {item.step}
                  </Box>
                  <Typography variant="h6" fontWeight="bold" sx={{ mt: 2 }}>
                    {item.title}
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 1 }}
                  >
                    {item.description}
                  </Typography>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>

        {/* CTA Card */}
        <Card
          sx={{
            mt: 3,
            borderRadius: 3,
            boxShadow: "none",
            border: "1px solid #e5e7eb",
          }}
        >
          <CardContent sx={{ p: { xs: 3, sm: 4 }, textAlign: "center" }}>
            <Typography variant="h6" fontWeight="bold">
              Ready to Start Earning?
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
              Join hundreds of affiliates already earning with BVIRAL
            </Typography>
            <Button
              variant="contained"
              endIcon={<ExternalLink style={{ width: 16, height: 16 }} />}
              sx={{
                mt: 3,
                bgcolor: "#111827",
                "&:hover": { bgcolor: "#1f2937" },
                textTransform: "none",
                fontWeight: 600,
                borderRadius: "9999px",
              }}
            >
              Get Started Now
            </Button>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}
