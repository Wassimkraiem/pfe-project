"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { CheckCircle2, Clock3, Film, Link as LinkIcon, XCircle } from "lucide-react";

import { getApiToken } from "@/lib/auth";
import {
  getAdminSubmissions,
  updateAdminSubmission,
  type VideoSubmission,
} from "@/lib/api";

type SubmissionStatus = VideoSubmission["status"];

const statusConfig: Record<
  SubmissionStatus,
  { label: string; color: string; bg: string; Icon: typeof Clock3 }
> = {
  pending: {
    label: "Pending",
    color: "#b45309",
    bg: "#fff7ed",
    Icon: Clock3,
  },
  approved: {
    label: "Approved",
    color: "#15803d",
    bg: "#f0fdf4",
    Icon: CheckCircle2,
  },
  rejected: {
    label: "Rejected",
    color: "#b91c1c",
    bg: "#fef2f2",
    Icon: XCircle,
  },
};

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function getSubmitterLabel(submission: VideoSubmission): string {
  const first = submission.user?.first_name?.trim();
  const last = submission.user?.last_name?.trim();
  const full = [first, last].filter(Boolean).join(" ").trim();
  return full || submission.user?.email?.trim() || "Submitter hidden by current API";
}

export default function AdminVideosPage() {
  const { getToken } = useAuth();
  const [submissions, setSubmissions] = useState<VideoSubmission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | SubmissionStatus>("all");
  const [search, setSearch] = useState("");
  const [draftNotes, setDraftNotes] = useState<Record<number, string>>({});
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const token = await getApiToken(getToken);
        if (!token) throw new Error("Missing auth token.");
        const items = await getAdminSubmissions(token);
        if (!active) return;
        setSubmissions(items);
        setDraftNotes(
          Object.fromEntries(
            items.map((item) => [item.id, item.admin_notes ?? ""]),
          ),
        );
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof Error ? err.message : "Failed to load submitted videos.",
        );
      } finally {
        if (active) setLoading(false);
      }
    };
    load();
    return () => {
      active = false;
    };
  }, [getToken]);

  const filteredSubmissions = useMemo(() => {
    return submissions.filter((submission) => {
      const haystack = [
        submission.title,
        submission.description ?? "",
        submission.category ?? "",
        submission.video_url,
        submission.user?.email ?? "",
        submission.user?.first_name ?? "",
        submission.user?.last_name ?? "",
      ]
        .join(" ")
        .toLowerCase();

      const matchesSearch =
        !search.trim() || haystack.includes(search.trim().toLowerCase());
      const matchesStatus =
        statusFilter === "all" || submission.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [search, statusFilter, submissions]);

  const handleUpdate = async (submissionId: number, status: SubmissionStatus) => {
    try {
      setUpdatingId(submissionId);
      setError(null);
      const token = await getApiToken(getToken);
      if (!token) throw new Error("Missing auth token.");
      const updated = await updateAdminSubmission(token, submissionId, {
        status,
        admin_notes: draftNotes[submissionId] ?? "",
      });
      setSubmissions((current) =>
        current.map((item) => (item.id === submissionId ? updated : item)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update submission.");
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          gap: 2,
          flexDirection: { xs: "column", lg: "row" },
        }}
      >
        <Box>
          <Typography fontSize={28} fontWeight={800} color="#111827">
            Submitted Videos
          </Typography>
          <Typography fontSize={14} color="text.secondary" sx={{ mt: 0.75 }}>
            Review user-submitted clips and approve or reject them.
          </Typography>
        </Box>
      </Box>

      {error ? (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      ) : null}

      <Card
        variant="outlined"
        sx={{ mt: 3, borderRadius: 3, borderColor: "#e5e7eb" }}
      >
        <CardContent sx={{ p: 2.5 }}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={1.5}
            alignItems={{ md: "center" }}
          >
            <TextField
              fullWidth
              size="small"
              label="Search submissions"
              placeholder="Title, URL, category, submitter..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <TextField
              select
              size="small"
              label="Status"
              value={statusFilter}
              onChange={(event) =>
                setStatusFilter(event.target.value as "all" | SubmissionStatus)
              }
              sx={{ minWidth: { md: 180 } }}
            >
              <MenuItem value="all">All statuses</MenuItem>
              <MenuItem value="pending">Pending</MenuItem>
              <MenuItem value="approved">Approved</MenuItem>
              <MenuItem value="rejected">Rejected</MenuItem>
            </TextField>
          </Stack>
        </CardContent>
      </Card>

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress size={28} sx={{ color: "#4D8AFF" }} />
        </Box>
      ) : filteredSubmissions.length === 0 ? (
        <Card
          variant="outlined"
          sx={{ mt: 3, borderRadius: 3, borderColor: "#e5e7eb" }}
        >
          <CardContent sx={{ py: 6 }}>
            <Typography align="center" fontSize={14} color="text.secondary">
              No submitted videos match the current filters.
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Box sx={{ mt: 3, display: "grid", gap: 2 }}>
          {filteredSubmissions.map((submission) => {
            const cfg = statusConfig[submission.status];
            const isUpdating = updatingId === submission.id;
            const url = /^https?:\/\//i.test(submission.video_url)
              ? submission.video_url
              : `https://${submission.video_url}`;

            return (
              <Card
                key={submission.id}
                variant="outlined"
                sx={{
                  borderRadius: 3,
                  borderColor: "#e5e7eb",
                  overflow: "hidden",
                }}
              >
                <CardContent sx={{ p: { xs: 2, sm: 2.5 } }}>
                  <Stack
                    direction={{ xs: "column", lg: "row" }}
                    spacing={2}
                    justifyContent="space-between"
                  >
                    <Box sx={{ minWidth: 0, flex: 1 }}>
                      <Stack
                        direction={{ xs: "column", sm: "row" }}
                        spacing={1}
                        alignItems={{ xs: "flex-start", sm: "center" }}
                        sx={{ mb: 1.25 }}
                      >
                        <Box
                          sx={{
                            width: 42,
                            height: 42,
                            borderRadius: 2.5,
                            display: "grid",
                            placeItems: "center",
                            bgcolor: "#eff6ff",
                            color: "#1d4ed8",
                            flexShrink: 0,
                          }}
                        >
                          <Film style={{ width: 18, height: 18 }} />
                        </Box>
                        <Box sx={{ minWidth: 0 }}>
                          <Typography fontSize={18} fontWeight={800} color="#111827" noWrap>
                            {submission.title}
                          </Typography>
                          <Typography fontSize={12} color="text.secondary">
                            Submitted by {getSubmitterLabel(submission)} on {formatDate(submission.created_at)}
                          </Typography>
                        </Box>
                      </Stack>

                      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", mb: 1.5 }}>
                        <Chip
                          icon={<cfg.Icon style={{ width: 14, height: 14, color: cfg.color }} />}
                          label={cfg.label}
                          size="small"
                          sx={{
                            bgcolor: cfg.bg,
                            color: cfg.color,
                            border: "1px solid",
                            borderColor: cfg.color,
                            fontWeight: 700,
                          }}
                        />
                        {submission.category ? (
                          <Chip
                            size="small"
                            label={submission.category}
                            sx={{ bgcolor: "#f8fafc" }}
                          />
                        ) : null}
                        {(submission.tags ?? []).map((tag) => (
                          <Chip
                            key={tag}
                            size="small"
                            label={tag}
                            sx={{ bgcolor: "#f8fafc" }}
                          />
                        ))}
                      </Stack>

                      {submission.description ? (
                        <Typography
                          fontSize={13}
                          color="text.secondary"
                          sx={{ whiteSpace: "pre-wrap" }}
                        >
                          {submission.description}
                        </Typography>
                      ) : (
                        <Typography fontSize={13} color="text.secondary">
                          No description provided.
                        </Typography>
                      )}

                      <Box
                        component="a"
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        sx={{
                          mt: 1.5,
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 0.75,
                          color: "#2563eb",
                          textDecoration: "none",
                          fontSize: 13,
                          fontWeight: 700,
                          "&:hover": { textDecoration: "underline" },
                        }}
                      >
                        <LinkIcon style={{ width: 14, height: 14 }} />
                        Open submitted video URL
                      </Box>
                    </Box>

                    <Box sx={{ width: { xs: "100%", lg: 340 }, flexShrink: 0 }}>
                      <TextField
                        fullWidth
                        multiline
                        minRows={4}
                        label="Admin notes"
                        value={draftNotes[submission.id] ?? ""}
                        onChange={(event) =>
                          setDraftNotes((current) => ({
                            ...current,
                            [submission.id]: event.target.value,
                          }))
                        }
                        placeholder="Optional moderation notes..."
                      />
                      <Stack direction="row" spacing={1} sx={{ mt: 1.25 }}>
                        <Button
                          fullWidth
                          variant="contained"
                          color="success"
                          disabled={isUpdating}
                          onClick={() => handleUpdate(submission.id, "approved")}
                          startIcon={
                            isUpdating ? (
                              <CircularProgress size={14} color="inherit" />
                            ) : (
                              <CheckCircle2 style={{ width: 14, height: 14 }} />
                            )
                          }
                          sx={{ textTransform: "none", borderRadius: 2 }}
                        >
                          Approve
                        </Button>
                        <Button
                          fullWidth
                          variant="outlined"
                          color="error"
                          disabled={isUpdating}
                          onClick={() => handleUpdate(submission.id, "rejected")}
                          startIcon={<XCircle style={{ width: 14, height: 14 }} />}
                          sx={{ textTransform: "none", borderRadius: 2 }}
                        >
                          Reject
                        </Button>
                      </Stack>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>
            );
          })}
        </Box>
      )}
    </Box>
  );
}
