"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  CircularProgress,
  FormControlLabel,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { BookOpen, Plus, Save, Search, Trash2 } from "lucide-react";

import {
  createFaq,
  deleteFaq,
  getAdminFaqs,
  searchFaqs,
  updateFaq,
  type FaqRecord,
} from "@/lib/api";
import { faqSeeds } from "@/lib/faqSeeds";

type EditableFaq = FaqRecord & {
  category: string;
  is_published: boolean;
  display_order: number;
};

type NewFaqDraft = {
  question: string;
  answer: string;
  category: string;
  display_order: number;
  is_published: boolean;
};

const emptyDraft: NewFaqDraft = {
  question: "",
  answer: "",
  category: "",
  display_order: 0,
  is_published: true,
};

function normalizeFaq(item: FaqRecord): EditableFaq {
  return {
    ...item,
    category: item.category ?? "",
    is_published: item.is_published ?? true,
    display_order: item.display_order ?? 0,
  };
}

function sortFaqs(items: EditableFaq[]): EditableFaq[] {
  if (items.some((item) => item.score !== null && item.score !== undefined)) {
    return [...items].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  }
  return [...items].sort((a, b) => a.display_order - b.display_order);
}

export default function AdminFaqsPage() {
  const [faqs, setFaqs] = useState<EditableFaq[]>(sortFaqs(faqSeeds.map(normalizeFaq)));
  const [newFaq, setNewFaq] = useState<NewFaqDraft>(emptyDraft);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [activeQuery, setActiveQuery] = useState("");

  useEffect(() => {
    let active = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      setNotice(null);
      try {
        const result = activeQuery.trim()
          ? await searchFaqs({ query: activeQuery.trim(), limit: 30 })
          : await getAdminFaqs({ limit: 100 });
        if (!active) return;
        if (result.items.length > 0) {
          setFaqs(sortFaqs(result.items.map(normalizeFaq)));
          setNotice(
            activeQuery.trim()
              ? `Showing semantic matches for "${activeQuery.trim()}".`
              : null,
          );
        } else {
          setFaqs(sortFaqs(faqSeeds.map(normalizeFaq)));
          setNotice(
            activeQuery.trim()
              ? `No vector matches were found for "${activeQuery.trim()}". Showing seeded FAQs instead.`
              : "FAQ API returned no items, so seeded FAQs are displayed.",
          );
        }
      } catch (err) {
        if (!active) return;
        setFaqs(sortFaqs(faqSeeds.map(normalizeFaq)));
        setNotice(
          err instanceof Error
            ? `FAQ API is not available yet. Showing seeded FAQs until it is ready: ${err.message}`
            : "FAQ API is not available yet. Showing seeded FAQs until it is ready.",
        );
      } finally {
        if (active) setLoading(false);
      }
    };
    load();
    return () => {
      active = false;
    };
  }, [activeQuery]);

  const publishedCount = useMemo(() => {
    return faqs.filter((item) => item.is_published).length;
  }, [faqs]);

  const handleSave = async (faq: EditableFaq) => {
    try {
      setSavingId(faq.id);
      setError(null);
      const updated = await updateFaq(faq.id, {
        question: faq.question,
        answer: faq.answer,
        category: faq.category || null,
        display_order: faq.display_order,
        is_published: faq.is_published,
      });
      const normalized = normalizeFaq(updated);
      setFaqs((current) =>
        sortFaqs(current.map((item) => (item.id === faq.id ? normalized : item))),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save FAQ.");
    } finally {
      setSavingId(null);
    }
  };

  const handleDelete = async (faqId: string) => {
    try {
      setDeletingId(faqId);
      setError(null);
      await deleteFaq(faqId);
      setFaqs((current) => current.filter((item) => item.id !== faqId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete FAQ.");
    } finally {
      setDeletingId(null);
    }
  };

  const handleCreate = async () => {
    if (!newFaq.question.trim() || !newFaq.answer.trim()) {
      setError("Question and answer are required.");
      return;
    }
    try {
      setCreating(true);
      setError(null);
      const created = await createFaq({
        question: newFaq.question.trim(),
        answer: newFaq.answer.trim(),
        category: newFaq.category.trim() || null,
        display_order: newFaq.display_order,
        is_published: newFaq.is_published,
      });
      setFaqs((current) => sortFaqs([normalizeFaq(created), ...current]));
      setNewFaq(emptyDraft);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create FAQ.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <Box>
      <Box>
        <Typography fontSize={28} fontWeight={800} color="#111827">
          FAQ Manager
        </Typography>
        <Typography fontSize={14} color="text.secondary" sx={{ mt: 0.75 }}>
          Add, update, publish, search, or delete FAQ entries for the support area.
        </Typography>
      </Box>

      {notice ? (
        <Alert severity="info" sx={{ mt: 2 }}>
          {notice}
        </Alert>
      ) : null}

      {error ? (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      ) : null}

      <Box
        sx={{
          mt: 3,
          display: "grid",
          gridTemplateColumns: { xs: "1fr", xl: "360px minmax(0, 1fr)" },
          gap: 2,
        }}
      >
        <Card variant="outlined" sx={{ borderRadius: 3, borderColor: "#e5e7eb" }}>
          <CardContent sx={{ p: 2.5 }}>
            <Stack direction="row" spacing={1} alignItems="center">
              <Box
                sx={{
                  width: 42,
                  height: 42,
                  borderRadius: 2.5,
                  display: "grid",
                  placeItems: "center",
                  bgcolor: "#eef2ff",
                  color: "#4338ca",
                }}
              >
                <BookOpen style={{ width: 18, height: 18 }} />
              </Box>
              <Box>
                <Typography fontSize={16} fontWeight={800}>
                  Create FAQ
                </Typography>
                <Typography fontSize={12} color="text.secondary">
                  {publishedCount} published now
                </Typography>
              </Box>
            </Stack>

            <Stack
              component="form"
              direction={{ xs: "column", sm: "row" }}
              spacing={1}
              sx={{ mt: 2 }}
              onSubmit={(event) => {
                event.preventDefault();
                setActiveQuery(searchInput);
              }}
            >
              <TextField
                fullWidth
                size="small"
                label="Semantic search"
                placeholder="Search the FAQ knowledge base"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />
              <Button
                type="submit"
                variant="outlined"
                startIcon={<Search style={{ width: 14, height: 14 }} />}
                sx={{ textTransform: "none", borderRadius: 999, minWidth: { sm: 124 } }}
              >
                Search
              </Button>
            </Stack>
            {activeQuery ? (
              <Button
                type="button"
                variant="text"
                onClick={() => {
                  setSearchInput("");
                  setActiveQuery("");
                }}
                sx={{ mt: 0.5, textTransform: "none", borderRadius: 999, px: 0 }}
              >
                Clear search
              </Button>
            ) : null}

            <Stack spacing={1.25} sx={{ mt: 2 }}>
              <TextField
                label="Question"
                value={newFaq.question}
                onChange={(event) =>
                  setNewFaq((current) => ({ ...current, question: event.target.value }))
                }
              />
              <TextField
                label="Answer"
                value={newFaq.answer}
                onChange={(event) =>
                  setNewFaq((current) => ({ ...current, answer: event.target.value }))
                }
                multiline
                minRows={5}
              />
              <TextField
                label="Category"
                value={newFaq.category}
                onChange={(event) =>
                  setNewFaq((current) => ({ ...current, category: event.target.value }))
                }
              />
              <TextField
                type="number"
                label="Display order"
                value={newFaq.display_order}
                onChange={(event) =>
                  setNewFaq((current) => ({
                    ...current,
                    display_order: Number(event.target.value) || 0,
                  }))
                }
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={newFaq.is_published}
                    onChange={(event) =>
                      setNewFaq((current) => ({
                        ...current,
                        is_published: event.target.checked,
                      }))
                    }
                  />
                }
                label="Publish immediately"
              />
              <Button
                variant="contained"
                onClick={handleCreate}
                disabled={creating}
                startIcon={
                  creating ? (
                    <CircularProgress size={14} color="inherit" />
                  ) : (
                    <Plus style={{ width: 14, height: 14 }} />
                  )
                }
                sx={{
                  textTransform: "none",
                  borderRadius: 2,
                  bgcolor: "#111827",
                  "&:hover": { bgcolor: "#1f2937" },
                }}
              >
                {creating ? "Creating..." : "Create FAQ"}
              </Button>
            </Stack>
          </CardContent>
        </Card>

        <Box sx={{ display: "grid", gap: 2 }}>
          {loading ? (
            <Card variant="outlined" sx={{ borderRadius: 3, borderColor: "#e5e7eb" }}>
              <CardContent sx={{ py: 8, display: "flex", justifyContent: "center" }}>
                <CircularProgress size={28} sx={{ color: "#4D8AFF" }} />
              </CardContent>
            </Card>
          ) : faqs.length === 0 ? (
            <Card variant="outlined" sx={{ borderRadius: 3, borderColor: "#e5e7eb" }}>
              <CardContent sx={{ py: 6 }}>
                <Typography align="center" fontSize={14} color="text.secondary">
                  No FAQs available yet.
                </Typography>
              </CardContent>
            </Card>
          ) : (
            faqs.map((faq) => {
              const isSaving = savingId === faq.id;
              const isDeleting = deletingId === faq.id;
              return (
                <Card
                  key={faq.id}
                  variant="outlined"
                  sx={{ borderRadius: 3, borderColor: "#e5e7eb" }}
                >
                  <CardContent sx={{ p: 2.5 }}>
                    <Stack spacing={1.25}>
                      <TextField
                        label="Question"
                        value={faq.question}
                        onChange={(event) =>
                          setFaqs((current) =>
                            current.map((item) =>
                              item.id === faq.id
                                ? { ...item, question: event.target.value }
                                : item,
                            ),
                          )
                        }
                      />
                      <TextField
                        label="Answer"
                        value={faq.answer}
                        onChange={(event) =>
                          setFaqs((current) =>
                            current.map((item) =>
                              item.id === faq.id
                                ? { ...item, answer: event.target.value }
                                : item,
                            ),
                          )
                        }
                        multiline
                        minRows={4}
                      />
                      <Stack direction={{ xs: "column", md: "row" }} spacing={1.25}>
                        <TextField
                          fullWidth
                          label="Category"
                          value={faq.category}
                          onChange={(event) =>
                            setFaqs((current) =>
                              current.map((item) =>
                                item.id === faq.id
                                  ? { ...item, category: event.target.value }
                                  : item,
                              ),
                            )
                          }
                        />
                        <TextField
                          type="number"
                          label="Order"
                          value={faq.display_order}
                          onChange={(event) =>
                            setFaqs((current) =>
                              current.map((item) =>
                                item.id === faq.id
                                  ? {
                                      ...item,
                                      display_order: Number(event.target.value) || 0,
                                    }
                                  : item,
                              ),
                            )
                          }
                          sx={{ width: { md: 140 } }}
                        />
                      </Stack>
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={faq.is_published}
                            onChange={(event) =>
                              setFaqs((current) =>
                                current.map((item) =>
                                  item.id === faq.id
                                    ? {
                                        ...item,
                                        is_published: event.target.checked,
                                      }
                                    : item,
                                ),
                              )
                            }
                          />
                        }
                        label="Published"
                      />
                      <Stack direction="row" spacing={1}>
                        <Button
                          variant="contained"
                          onClick={() => handleSave(faq)}
                          disabled={isSaving || isDeleting}
                          startIcon={
                            isSaving ? (
                              <CircularProgress size={14} color="inherit" />
                            ) : (
                              <Save style={{ width: 14, height: 14 }} />
                            )
                          }
                          sx={{
                            textTransform: "none",
                            borderRadius: 2,
                            bgcolor: "#111827",
                            "&:hover": { bgcolor: "#1f2937" },
                          }}
                        >
                          {isSaving ? "Saving..." : "Save"}
                        </Button>
                        <Button
                          variant="outlined"
                          color="error"
                          onClick={() => handleDelete(faq.id)}
                          disabled={isSaving || isDeleting}
                          startIcon={
                            isDeleting ? (
                              <CircularProgress size={14} color="inherit" />
                            ) : (
                              <Trash2 style={{ width: 14, height: 14 }} />
                            )
                          }
                          sx={{ textTransform: "none", borderRadius: 2 }}
                        >
                          {isDeleting ? "Deleting..." : "Delete"}
                        </Button>
                      </Stack>
                      {faq.score !== null && faq.score !== undefined ? (
                        <Typography fontSize={11} color="text.secondary">
                          Search score: {faq.score.toFixed(3)}
                        </Typography>
                      ) : null}
                    </Stack>
                  </CardContent>
                </Card>
              );
            })
          )}
        </Box>
      </Box>
    </Box>
  );
}
