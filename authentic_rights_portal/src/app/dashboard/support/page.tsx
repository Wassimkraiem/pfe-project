"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Mail, HelpCircle, CreditCard, Search } from "lucide-react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { getFaqs, searchFaqs, type FaqRecord } from "@/lib/api";
import { faqSeeds } from "@/lib/faqSeeds";

function sortFaqs(items: FaqRecord[]): FaqRecord[] {
  if (items.some((item) => item.score !== null && item.score !== undefined)) {
    return [...items].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  }
  return [...items].sort((a, b) => (a.display_order ?? 9999) - (b.display_order ?? 9999));
}

export default function SupportPage() {
  const [faqs, setFaqs] = useState<FaqRecord[]>(sortFaqs(faqSeeds));
  const [loadingFaqs, setLoadingFaqs] = useState(true);
  const [faqNotice, setFaqNotice] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [activeQuery, setActiveQuery] = useState("");

  useEffect(() => {
    let active = true;
    const load = async () => {
      setLoadingFaqs(true);
      try {
        const result = activeQuery.trim()
          ? await searchFaqs({ query: activeQuery.trim(), limit: 20 })
          : await getFaqs({ limit: 50 });
        if (!active) return;
        if (result.items.length > 0) {
          setFaqs(sortFaqs(result.items));
          setFaqNotice(
            activeQuery.trim()
              ? `Showing semantic matches for "${activeQuery.trim()}".`
              : null,
          );
        } else {
          setFaqs(sortFaqs(faqSeeds));
          setFaqNotice(
            activeQuery.trim()
              ? `No vector matches were found for "${activeQuery.trim()}". Showing the fallback FAQ list instead.`
              : "FAQ API returned no items, so the fallback list is shown.",
          );
        }
      } catch {
        if (!active) return;
        setFaqs(sortFaqs(faqSeeds));
        setFaqNotice(
          activeQuery.trim()
            ? "FAQ search is not available yet, so the fallback list is shown."
            : "FAQ API is not available yet, so the fallback list is shown.",
        );
      } finally {
        if (active) setLoadingFaqs(false);
      }
    };
    load();
    return () => {
      active = false;
    };
  }, [activeQuery]);

  const faqCountLabel = useMemo(() => {
    return `${faqs.length} article${faqs.length === 1 ? "" : "s"}`;
  }, [faqs]);

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#fafafa" }}>
      <Box sx={{ px: { xs: 2, sm: 3, lg: 4 }, py: { xs: 4, sm: 6 } }}>
        <Box>
          <Typography
            variant="h5"
            fontWeight="bold"
            sx={{ fontSize: { xs: "1.5rem", sm: "1.875rem" } }}
          >
            Support & Help
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
            Get help with your account, channels, and subscription.
          </Typography>
        </Box>

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
              Need help with approvals, subscription updates, or channel access? The BVIRAL team can assist directly.
            </Typography>
            <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 1.25 }}>
              <Button
                href="mailto:sales@bviral.com"
                variant="contained"
                startIcon={<Mail style={{ width: 16, height: 16 }} />}
                sx={{
                  bgcolor: "#111827",
                  "&:hover": { bgcolor: "#1f2937" },
                  textTransform: "none",
                  fontWeight: 600,
                  borderRadius: "9999px",
                }}
              >
                Email sales@bviral.com
              </Button>
              <Button
                component={Link}
                href="/dashboard/subscription"
                variant="outlined"
                startIcon={<CreditCard style={{ width: 16, height: 16 }} />}
                sx={{
                  textTransform: "none",
                  fontWeight: 600,
                  borderRadius: "9999px",
                }}
              >
                Manage Subscription
              </Button>
            </Box>
          </CardContent>
        </Card>

        <Card
          sx={{
            mt: 4,
            borderRadius: 3,
            boxShadow: "none",
            border: "1px solid #e5e7eb",
          }}
        >
          <CardContent sx={{ p: 3 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: { xs: "flex-start", sm: "center" },
                justifyContent: "space-between",
                gap: 1.5,
                flexDirection: { xs: "column", sm: "row" },
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <HelpCircle style={{ width: 20, height: 20 }} />
                <Typography variant="h6" fontWeight="bold">
                  Frequently Asked Questions
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                {faqCountLabel}
              </Typography>
            </Box>

            <Stack
              component="form"
              direction={{ xs: "column", sm: "row" }}
              spacing={1}
              sx={{ mt: 2.5 }}
              onSubmit={(event) => {
                event.preventDefault();
                setActiveQuery(searchInput);
              }}
            >
              <TextField
                fullWidth
                size="small"
                label="Search FAQs"
                placeholder="Ask about billing, channels, licensing..."
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />
              <Button
                type="submit"
                variant="outlined"
                startIcon={<Search style={{ width: 14, height: 14 }} />}
                sx={{ textTransform: "none", borderRadius: 999, minWidth: { sm: 130 } }}
              >
                Search
              </Button>
              {activeQuery ? (
                <Button
                  type="button"
                  variant="text"
                  onClick={() => {
                    setSearchInput("");
                    setActiveQuery("");
                  }}
                  sx={{ textTransform: "none", borderRadius: 999 }}
                >
                  Clear
                </Button>
              ) : null}
            </Stack>

            {faqNotice ? (
              <Alert severity="info" sx={{ mt: 2 }}>
                {faqNotice}
              </Alert>
            ) : null}

            {loadingFaqs ? (
              <Box sx={{ display: "flex", justifyContent: "center", py: 5 }}>
                <CircularProgress size={24} sx={{ color: "#4D8AFF" }} />
              </Box>
            ) : (
              <Box sx={{ mt: 3, display: "flex", flexDirection: "column", gap: 1 }}>
                {faqs.map((faq) => (
                  <Box
                    key={faq.id}
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      border: "1px solid #e5e7eb",
                      bgcolor: "#fff",
                    }}
                  >
                    <Typography fontWeight="bold">{faq.question}</Typography>
                    {faq.category ? (
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
                        {faq.category}
                      </Typography>
                    ) : null}
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ mt: 1, whiteSpace: "pre-wrap" }}
                    >
                      {faq.answer}
                    </Typography>
                  </Box>
                ))}
              </Box>
            )}
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}
