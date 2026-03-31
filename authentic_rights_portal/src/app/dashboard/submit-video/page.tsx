"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Upload, CheckCircle, Clock, XCircle } from "lucide-react";
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  TextField,
  CircularProgress,
  Alert,
  Chip,
  Divider,
} from "@mui/material";

import { getApiToken, type GetTokenFn } from "@/lib/auth";
import { submitVideo, getMySubmissions, type VideoSubmission } from "@/lib/api";

const statusCfg = {
  pending:  { label: "Pending",  color: "#f59e0b", Icon: Clock },
  approved: { label: "Approved", color: "#10b981", Icon: CheckCircle },
  rejected: { label: "Rejected", color: "#ef4444", Icon: XCircle },
} as const;

export default function SubmitVideoPage() {
  const { getToken } = useAuth();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [category, setCategory] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const [submissions, setSubmissions] = useState<VideoSubmission[]>([]);
  const [loadingSubs, setLoadingSubs] = useState(true);

  const fetchSubmissions = useCallback(async () => {
    try {
      setLoadingSubs(true);
      const token = await getApiToken(getToken as GetTokenFn);
      if (!token) return;
      setSubmissions(await getMySubmissions(token));
    } catch { /* silent */ }
    finally { setLoadingSubs(false); }
  }, [getToken]);

  useEffect(() => { fetchSubmissions(); }, [fetchSubmissions]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !videoUrl.trim()) return;
    try {
      setSubmitting(true); setError(""); setSuccess(false);
      const token = await getApiToken(getToken as GetTokenFn);
      if (!token) return;
      const tags = tagsInput.split(",").map((t) => t.trim()).filter(Boolean);
      await submitVideo(token, {
        title: title.trim(),
        description: description.trim() || undefined,
        video_url: videoUrl.trim(),
        tags: tags.length > 0 ? tags : undefined,
        category: category.trim() || undefined,
      });
      setSuccess(true); setTitle(""); setDescription(""); setVideoUrl(""); setTagsInput(""); setCategory("");
      await fetchSubmissions();
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to submit video"); }
    finally { setSubmitting(false); }
  };

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
        <Upload style={{ width: 20, height: 20, color: "#111827" }} />
        <Typography fontSize={18} fontWeight={700} color="#111827">Submit a Video</Typography>
      </Box>
      <Typography fontSize={13} color="text.secondary" sx={{ mb: 2 }}>
        Add your video to the BVIRAL library for others to discover, license, and use.
      </Typography>

      {success && <Alert severity="success" sx={{ mb: 1.5, py: 0, fontSize: 13 }}>Submitted! Our team will review it shortly.</Alert>}
      {error && <Alert severity="error" sx={{ mb: 1.5, py: 0, fontSize: 13 }}>{error}</Alert>}

      <Card variant="outlined" sx={{ borderRadius: 1.5, mb: 3 }}>
        <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
          <Box component="form" onSubmit={handleSubmit} sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
            <Box sx={{ display: "flex", gap: 1.5 }}>
              <TextField label="Video Title" value={title} onChange={(e) => setTitle(e.target.value)} required fullWidth size="small" />
              <TextField label="Category" value={category} onChange={(e) => setCategory(e.target.value)} fullWidth size="small" placeholder="Animals, Sports..." sx={{ maxWidth: 200 }} />
            </Box>
            <TextField label="Video URL" value={videoUrl} onChange={(e) => setVideoUrl(e.target.value)} required fullWidth size="small" placeholder="https://..." />
            <Box sx={{ display: "flex", gap: 1.5 }}>
              <TextField label="Description" value={description} onChange={(e) => setDescription(e.target.value)} multiline rows={2} fullWidth size="small" />
              <TextField label="Tags (comma separated)" value={tagsInput} onChange={(e) => setTagsInput(e.target.value)} fullWidth size="small" placeholder="funny, viral" sx={{ maxWidth: 220 }} />
            </Box>
            <Button
              type="submit" variant="contained" disabled={submitting || !title.trim() || !videoUrl.trim()}
              startIcon={submitting ? <CircularProgress size={14} color="inherit" /> : <Upload style={{ width: 14, height: 14 }} />}
              sx={{ alignSelf: "flex-start", bgcolor: "#111827", "&:hover": { bgcolor: "#1f2937" }, textTransform: "none", fontWeight: 600, borderRadius: "9999px", px: 2.5, py: 0.6, fontSize: 13 }}
            >
              {submitting ? "Submitting…" : "Submit Video"}
            </Button>
          </Box>
        </CardContent>
      </Card>

      <Divider sx={{ mb: 2 }} />

      <Typography fontSize={15} fontWeight={600} color="#111827" sx={{ mb: 1.5 }}>My Submissions</Typography>

      {loadingSubs ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}><CircularProgress size={22} sx={{ color: "#4D8AFF" }} /></Box>
      ) : submissions.length === 0 ? (
        <Typography fontSize={12} color="text.secondary">No submissions yet.</Typography>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
          {submissions.map((sub) => {
            const cfg = statusCfg[sub.status];
            return (
              <Box key={sub.id} sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 1.5, py: 0.75, border: "1px solid #e5e7eb", borderRadius: 1.5 }}>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography fontSize={13} fontWeight={600} color="#111827" noWrap>{sub.title}</Typography>
                  <Typography fontSize={11} color="text.secondary" noWrap>
                    {new Date(sub.created_at).toLocaleDateString()}
                    {sub.description ? ` · ${sub.description}` : ""}
                  </Typography>
                </Box>
                <Chip
                  icon={<cfg.Icon style={{ width: 12, height: 12, color: cfg.color }} />}
                  label={cfg.label}
                  size="small"
                  variant="outlined"
                  sx={{ borderColor: cfg.color, color: cfg.color, fontWeight: 600, fontSize: 11, height: 24 }}
                />
              </Box>
            );
          })}
        </Box>
      )}
    </Box>
  );
}
