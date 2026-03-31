"use client";

import Link from "next/link";
import { Check, ArrowRight } from "lucide-react";
import { Box, Typography, Button } from "@mui/material";

const features = [
  "Unlimited Download Credits",
  "Video Editing Allowed",
  "Watermark-Free",
  "Approved For Monetization",
  "Organic Use",
];

const highlights = [
  "Approved For Monetization",
  "Watermark Free",
  "Access to Meta Data",
];

export default function Home() {
  return (
    <Box
      sx={{
        maxWidth: "80rem",
        mx: "auto",
        px: { xs: 2, sm: 3, lg: 4 },
        py: 8,
        minHeight: "calc(100vh - 120px)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
      }}
    >
      <Box
        sx={{
          display: "grid",
          gap: { xs: 6, lg: 8 },
          gridTemplateColumns: { lg: "repeat(2, 1fr)" },
          alignItems: "center",
        }}
      >
        {/* Left Column - Hero Content */}
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
          }}
        >
          <Typography
            variant="body2"
            fontWeight={500}
            sx={{ color: "#4D8AFF" }}
          >
            Over 90,000+ Viral Proven Videos
          </Typography>

          <Typography
            variant="h3"
            fontWeight="bold"
            sx={{
              mt: 2,
              fontSize: { xs: "2.25rem", sm: "3rem" },
              lineHeight: 1.2,
            }}
          >
            Affordable pricing.
            <br />
            Easy Scaling.
          </Typography>

          <Typography
            variant="body1"
            color="text.secondary"
            sx={{ mt: 3, maxWidth: "28rem", lineHeight: 1.6 }}
          >
            A BVIRAL content subscription is the easiest way to grow your brand
            and audience with minimal time and effort.
          </Typography>

          <Box sx={{ mt: 5, display: "flex", flexDirection: "column", gap: 2 }}>
            {highlights.map((item) => (
              <Box
                key={item}
                sx={{ display: "flex", alignItems: "center", gap: 1.5 }}
              >
                <Check style={{ width: 20, height: 20 }} strokeWidth={2} />
                <Typography fontWeight={500}>{item}</Typography>
              </Box>
            ))}
          </Box>
        </Box>

        {/* Right Column - Pricing Cards */}
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {/* Primary Pricing Card */}
          <Box
            sx={{ borderRadius: 4, bgcolor: "#4D8AFF", p: 4, color: "white" }}
          >
            <Box sx={{ mb: 0.5 }}>
              <Typography
                component="span"
                sx={{ fontSize: "3rem", fontWeight: "bold" }}
              >
                $399
              </Typography>
              <Typography
                component="span"
                sx={{ fontSize: "1.25rem", fontWeight: 500 }}
              >
                /month
              </Typography>
            </Box>
            <Typography
              variant="body2"
              sx={{ mb: 3, color: "rgba(255, 255, 255, 0.9)" }}
            >
              For Channels With Less Than 2M Followers
            </Typography>

            <Button
              component={Link}
              href="/signup"
              fullWidth
              variant="contained"
              endIcon={<ArrowRight style={{ width: 16, height: 16 }} />}
              sx={{
                mb: 4,
                py: 1.5,
                bgcolor: "white",
                color: "#4D8AFF",
                "&:hover": { bgcolor: "rgba(255, 255, 255, 0.9)" },
                textTransform: "none",
                fontWeight: 600,
                borderRadius: "9999px",
              }}
            >
              Get Started Now
            </Button>

            <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
              {features.map((feature) => (
                <Box
                  key={feature}
                  sx={{ display: "flex", alignItems: "center", gap: 1.5 }}
                >
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      bgcolor: "white",
                    }}
                  />
                  <Typography variant="body2">{feature}</Typography>
                </Box>
              ))}
            </Box>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
