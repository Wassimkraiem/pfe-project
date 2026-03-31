"use client";

import Link from "next/link";
import { Mail, HelpCircle } from "lucide-react";
import { Box, Typography, Button, Card, CardContent } from "@mui/material";
import type { ReactNode } from "react";

type FaqItem = {
  question: string;
  answer: ReactNode;
};

const ManageSubscriptionLink = () => (
  <Link
    href="/dashboard/subscription"
    style={{
      color: "#4D8AFF",
      textDecoration: "underline",
      fontWeight: 500,
    }}
  >
    Manage Subscription
  </Link>
);

const faqs: FaqItem[] = [
  {
    question: "How do I access the content library?",
    answer:
      "Click 'Open Content Portal' on the dashboard to access 90,000+ viral videos. You can search through the library using AI search, look through categories, and filter videos directly on the portal. Please be sure to only share the videos on your approved channels.",
  },
  {
    question: "Can I add or remove channels from my subscription?",
    answer:
      "Yes! Please contact sales@bviral.com with your request. Be sure to include the URL to any new channel you'd like to add.",
  },
  {
    question: "How does billing work?",
    answer: (
      <>
        Depending on your selections at checkout, you&apos;ll automatically be billed monthly or annually. To view or update your billing details, go to <ManageSubscriptionLink />.
      </>
    ),
  },
  {
    question: "What happens if I cancel my subscription?",
    answer:
      "You may keep the videos posted that were shared during your active subscription period, but you may not share any more BVIRAL videos on your channel(s) after your term ends. To cancel, simply email sales@bviral.com at least 30 days before the end of your current term.",
  },
  {
    question: "Can I change my plan?",
    answer: (
      <>
        You can switch to monthly or annual billing by visiting the <ManageSubscriptionLink /> page or contacting sales@bviral.com.
      </>
    ),
  },
  {
    question: "What if my channel username changed?",
    answer:
      "Contact sales@bviral.com immediately with your old and new username so we can update your whitelist right away.",
  },
];

export default function SupportPage() {
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
            Support & Help
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
            Get help with your account, channels, and subscription
          </Typography>
        </Box>

        {/* Contact Support Card */}
        <Card
          sx={{
            mt: 4,
            borderRadius: 3,
            boxShadow: "none",
            border: "1px solid #e5e7eb",
          }}
        >
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Mail style={{ width: 20, height: 20 }} />
              <Typography variant="h6" fontWeight="bold">
                Contact Support
              </Typography>
            </Box>
            <Typography variant="body1" color="text.secondary" sx={{ mt: 2 }}>
              Need help? Our support team is here to assist you with any
              questions or issues.
            </Typography>
            <Button
              href="mailto:sales@bviral.com"
              variant="contained"
              startIcon={<Mail style={{ width: 16, height: 16 }} />}
              sx={{
                mt: 2,
                bgcolor: "#111827",
                "&:hover": { bgcolor: "#1f2937" },
                textTransform: "none",
                fontWeight: 600,
                borderRadius: "9999px",
              }}
            >
              Email sales@bviral.com
            </Button>
          </CardContent>
        </Card>

        {/* FAQ Card */}
        <Card
          sx={{
            mt: 4,
            borderRadius: 3,
            boxShadow: "none",
            border: "1px solid #e5e7eb",
          }}
        >
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <HelpCircle style={{ width: 20, height: 20 }} />
              <Typography variant="h6" fontWeight="bold">
                Frequently Asked Questions
              </Typography>
            </Box>

            <Box
              sx={{ mt: 3, display: "flex", flexDirection: "column", gap: 1 }}
            >
              {faqs.map((faq, index) => (
                <Box
                  key={index}
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    border: "1px solid #e5e7eb",
                  }}
                >
                  <Typography fontWeight="bold">{faq.question}</Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 1 }}
                  >
                    {faq.answer}
                  </Typography>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}
