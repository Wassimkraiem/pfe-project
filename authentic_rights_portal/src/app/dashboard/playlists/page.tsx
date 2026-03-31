"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { ListVideo, Plus, Trash2, ChevronRight } from "lucide-react";
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  IconButton,
  Tooltip,
} from "@mui/material";

import { getApiToken, type GetTokenFn } from "@/lib/auth";
import {
  getPlaylists,
  createPlaylist,
  deletePlaylist,
  type PlaylistSummary,
} from "@/lib/api";

export default function PlaylistsPage() {
  const { getToken } = useAuth();
  const [playlists, setPlaylists] = useState<PlaylistSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [creating, setCreating] = useState(false);

  const fetchPlaylists = useCallback(async () => {
    try {
      setLoading(true);
      const token = await getApiToken(getToken as GetTokenFn);
      if (!token) return;
      const data = await getPlaylists(token);
      setPlaylists(data);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load playlists");
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => { fetchPlaylists(); }, [fetchPlaylists]);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    try {
      setCreating(true);
      const token = await getApiToken(getToken as GetTokenFn);
      if (!token) return;
      await createPlaylist(token, { title: newTitle.trim(), description: newDescription.trim() || undefined });
      setDialogOpen(false);
      setNewTitle("");
      setNewDescription("");
      await fetchPlaylists();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create playlist");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const token = await getApiToken(getToken as GetTokenFn);
      if (!token) return;
      await deletePlaylist(token, id);
      setPlaylists((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete playlist");
    }
  };

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <ListVideo style={{ width: 22, height: 22, color: "#111827" }} />
          <Typography fontSize={18} fontWeight={700} color="#111827">My Playlists</Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<Plus style={{ width: 15, height: 15 }} />}
          onClick={() => setDialogOpen(true)}
          sx={{ bgcolor: "#111827", "&:hover": { bgcolor: "#1f2937" }, textTransform: "none", fontWeight: 600, borderRadius: "9999px", px: 2, py: 0.6, fontSize: 13 }}
        >
          New Playlist
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 1.5, py: 0, fontSize: 13 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}><CircularProgress size={28} sx={{ color: "#4D8AFF" }} /></Box>
      ) : playlists.length === 0 ? (
        <Box sx={{ textAlign: "center", py: 6, border: "1px dashed #d1d5db", borderRadius: 2 }}>
          <ListVideo style={{ width: 36, height: 36, color: "#9ca3af", margin: "0 auto 8px" }} />
          <Typography fontSize={13} color="text.secondary" sx={{ mb: 0.25 }}>No playlists yet</Typography>
          <Typography fontSize={12} color="text.secondary">Create one or save videos from the search assistant.</Typography>
        </Box>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
          {playlists.map((pl) => (
            <Link key={pl.id} href={`/dashboard/playlists/${pl.id}`} style={{ textDecoration: "none" }}>
              <Box sx={{
                display: "flex", alignItems: "center", gap: 1.5, px: 1.5, py: 1,
                border: "1px solid #e5e7eb", borderRadius: 1.5,
                transition: "all 0.15s",
                "&:hover": { borderColor: "#d1d5db", bgcolor: "#fafafa" },
              }}>
                <Box sx={{ width: 36, height: 36, borderRadius: 1, bgcolor: "#f3f4f6", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <ListVideo style={{ width: 18, height: 18, color: "#6b7280" }} />
                </Box>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography fontSize={13} fontWeight={600} color="#111827" noWrap>{pl.title}</Typography>
                  <Typography fontSize={11} color="text.secondary" noWrap>
                    {pl.video_count} video{pl.video_count !== 1 ? "s" : ""}
                    {pl.description ? ` · ${pl.description}` : ""}
                  </Typography>
                </Box>
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.25, flexShrink: 0 }}>
                  <Tooltip title="Delete playlist">
                    <IconButton size="small" onClick={(e) => handleDelete(e, pl.id)} sx={{ color: "#9ca3af", width: 28, height: 28, "&:hover": { color: "#ef4444", bgcolor: "#fef2f2" } }}>
                      <Trash2 style={{ width: 14, height: 14 }} />
                    </IconButton>
                  </Tooltip>
                  <ChevronRight style={{ width: 16, height: 16, color: "#9ca3af" }} />
                </Box>
              </Box>
            </Link>
          ))}
        </Box>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="xs" fullWidth PaperProps={{ sx: { borderRadius: 2 } }}>
        <DialogTitle sx={{ fontSize: 15, fontWeight: 600, pb: 0.5 }}>New Playlist</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 1.5, pt: "8px !important" }}>
          <TextField label="Title" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} fullWidth required autoFocus size="small" />
          <TextField label="Description (optional)" value={newDescription} onChange={(e) => setNewDescription(e.target.value)} fullWidth multiline rows={2} size="small" />
        </DialogContent>
        <DialogActions sx={{ px: 2.5, pb: 1.5 }}>
          <Button onClick={() => setDialogOpen(false)} sx={{ textTransform: "none", fontSize: 13 }}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate} disabled={creating || !newTitle.trim()} sx={{ bgcolor: "#111827", "&:hover": { bgcolor: "#1f2937" }, textTransform: "none", fontSize: 13 }}>
            {creating ? "Creating…" : "Create"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
