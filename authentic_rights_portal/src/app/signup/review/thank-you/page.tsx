"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle, Mail, ArrowRight } from "lucide-react";
import { Box, Typography, Button, CircularProgress } from "@mui/material";

function ThankYouContent() {
  const searchParams = useSearchParams();
  const email = searchParams.get("email") || "your email";
  const nextSteps = [
    {
      number: 1,
      title: "Our team will review your channels",
      description:
        "We'll review your channels to determine the best plan for your needs",
    },
    {
      number: 2,
      title: "Receive your custom quote via email",
      description: "This is typically sent within 24-48 hours",
    },
    {
      number: 3,
      title: "Checkout and start posting",
      description:
        "Once you complete checkout, you'll get instant access to our library",
    },
  ];

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "white" }}>
      <Box
        sx={{
          maxWidth: "42rem",
          mx: "auto",
          px: 2,
          py: { xs: 4, sm: 6, lg: 8 },
        }}
      >
        <Box
          sx={{
            borderRadius: 4,
            border: "1px solid #e5e7eb",
            px: { xs: 3, sm: 5 },
            py: { xs: 5, sm: 7 },
          }}
        >
          <Box sx={{ display: "flex", justifyContent: "center" }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: { xs: 64, sm: 80 },
                height: { xs: 64, sm: 80 },
                borderRadius: "50%",
                bgcolor: "#dcfce7",
              }}
            >
              <CheckCircle
                style={{ width: 40, height: 40, color: "#22c55e" }}
                strokeWidth={1.5}
              />
            </Box>
          </Box>

          <Typography
            variant="h4"
            fontWeight="bold"
            sx={{
              mt: 3,
              textAlign: "center",
              fontSize: { xs: "1.875rem", sm: "2.25rem" },
            }}
          >
            Thank You!
          </Typography>
          <Typography
            variant="body1"
            color="text.secondary"
            sx={{
              mt: 1.5,
              textAlign: "center",
              fontSize: { xs: "1rem", sm: "1.125rem" },
            }}
          >
            Your custom quote request has been received.
          </Typography>

          <Box
            sx={{
              mt: { xs: 4, sm: 5 },
              px: { xs: 2.5, sm: 3 },
              py: { xs: 3, sm: 4 },
              borderRadius: 3,
              border: "1px solid #dbeafe",
              bgcolor: "rgba(239, 246, 255, 0.5)",
            }}
          >
            <Typography
              variant="h6"
              fontWeight="bold"
              sx={{
                textAlign: "center",
                fontSize: { xs: "1.125rem", sm: "1.25rem" },
              }}
            >
              What Happens Next?
            </Typography>

            <Box
              sx={{ mt: 3, display: "flex", flexDirection: "column", gap: 2.5 }}
            >
              {nextSteps.map((step) => (
                <Box key={step.number} sx={{ display: "flex", gap: 2 }}>
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: 28,
                      height: 28,
                      borderRadius: "50%",
                      bgcolor: "#4D8AFF",
                      color: "white",
                      fontSize: "0.875rem",
                      fontWeight: 600,
                      flexShrink: 0,
                    }}
                  >
                    {step.number}
                  </Box>
                  <Box sx={{ flex: 1, pt: 0.25 }}>
                    <Typography
                      fontWeight={600}
                      sx={{ fontSize: { xs: "0.875rem", sm: "1rem" } }}
                    >
                      {step.title}
                    </Typography>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ mt: 0.5 }}
                    >
                      {step.description}
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Box>
          </Box>

          <Box
            sx={{
              mt: 4,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 1,
            }}
          >
            <Mail style={{ width: 20, height: 20, color: "#9ca3af" }} />
            <Typography variant="body2" color="text.secondary">
              Check your email for confirmation at{" "}
              <Typography
                component="span"
                fontWeight={600}
                color="text.primary"
              >
                {email}
              </Typography>
            </Typography>
          </Box>

          <Box sx={{ mt: 3, display: "flex", justifyContent: "center" }}>
            <Button
              component={Link}
              href="https://bviral.com/subscriptions/"
              variant="contained"
              endIcon={<ArrowRight style={{ width: 20, height: 20 }} />}
              sx={{
                height: 48,
                px: 4,
                bgcolor: "#4D8AFF",
                "&:hover": { bgcolor: "#3D7AEF" },
                textTransform: "none",
                fontWeight: 600,
                borderRadius: "9999px",
              }}
            >
              Return Home
            </Button>
          </Box>

          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ mt: 3, textAlign: "center" }}
          >
            Questions? Contact us at{" "}
            <a
              href="mailto:sales@bviral.com"
              style={{
                fontWeight: 500,
                color: "#4D8AFF",
                textDecoration: "none",
              }}
            >
              sales@bviral.com
            </a>
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}

function LoadingFallback() {
  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "white",
      }}
    >
      <CircularProgress sx={{ color: "#4D8AFF" }} />
    </Box>
  );
}

export default function SignupReviewThankYouPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <ThankYouContent />
    </Suspense>
  );
}
