"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Trash2,
  Film,
  Play,
  Download,
  X,
} from "lucide-react";
import {
  Box,
  Typography,
  Button,
  Card,
  CardMedia,
  CircularProgress,
  Alert,
  IconButton,
  Chip,
  Dialog,
  DialogContent,
  Tooltip,
  Grid,
} from "@mui/material";

import { getApiToken, type GetTokenFn } from "@/lib/auth";
import {
  getPlaylist,
  removeVideoFromPlaylist,
  getVideosByIds,
  type PlaylistDetail,
  type VideoSearchResult,
} from "@/lib/api";

type VideoInfo = {
  video_id: string;
  title: string;
  description: string;
  durationFormatted: string;
  owner: string;
  thumbnail: string;
  playUrl: string;
  downloadUrl: string;
  dimensions: string;
};

function findServiceData(doc: Record<string, unknown>) {
  const preferred = ["cts", "ftp", "s3", "aws", "azure", "gcp", "cdn", "stream"];
  for (const key of preferred) {
    const svc = doc[key] as Record<string, unknown> | undefined;
    if (svc?.data) return svc;
  }
  for (const key of Object.keys(doc)) {
    const svc = doc[key] as Record<string, unknown> | undefined;
    if (svc && typeof svc === "object" && svc.data) return svc;
  }
  if (doc.data && typeof doc.data === "object") return { data: doc.data };
  return null;
}

function fmtDur(sec: number): string {
  if (!sec) return "";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function extractVideoInfo(doc: VideoSearchResult): VideoInfo {
  const raw = doc as Record<string, unknown>;
  const svc = findServiceData(raw);
  const d = (svc?.data ?? {}) as Record<string, unknown>;
  const add = (d.additional ?? {}) as Record<string, unknown>;
  const meta = (d.metadata ?? {}) as Record<string, unknown>;
  const def = (d.default ?? {}) as Record<string, unknown>;
  const u = (d.url ?? {}) as Record<string, unknown>;

  return {
    video_id: (raw.video_id as string) ?? "",
    title: (d.title as string) || (def.Name as string) || (d.name as string) || (add.Title as string) || "Untitled",
    description: ((add.Description as string) || (d.description as string) || "").slice(0, 160),
    durationFormatted: fmtDur((meta.duration as number) ?? (def.Time as number) ?? 0),
    owner: (d.ownerName as string) || "",
    thumbnail: (u.directUrlPreview as string) || (u.preview as string) || "",
    playUrl: (u.directUrlPreviewPlay as string) || (u.play as string) || "",
    downloadUrl: (u.download as string) || "",
    dimensions: `${d.width ?? meta.width ?? 0}x${d.height ?? meta.height ?? 0}`,
  };
}

function PlayerDialog({ video, open, onClose }: { video: VideoInfo | null; open: boolean; onClose: () => void }) {
  const ref = useRef<HTMLVideoElement>(null);
  useEffect(() => { if (!open && ref.current) ref.current.pause(); }, [open]);
  if (!video) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth PaperProps={{ sx: { borderRadius: 2.5, overflow: "hidden", bgcolor: "#000" } }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", px: 1.5, py: 0.75, bgcolor: "#111" }}>
        <Typography fontSize={13} fontWeight={600} color="white" noWrap sx={{ flex: 1, mr: 1 }}>{video.title}</Typography>
        <Box sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
          {video.downloadUrl && (
            <Tooltip title="Download">
              <IconButton component="a" href={video.downloadUrl} target="_blank" rel="noopener noreferrer" size="small" sx={{ color: "white" }}>
                <Download style={{ width: 15, height: 15 }} />
              </IconButton>
            </Tooltip>
          )}
          <IconButton onClick={onClose} size="small" sx={{ color: "white" }}>
            <X style={{ width: 16, height: 16 }} />
          </IconButton>
        </Box>
      </Box>
      <DialogContent sx={{ p: 0, bgcolor: "#000" }}>
        {video.playUrl ? (
          <video ref={ref} src={video.playUrl} controls autoPlay poster={video.thumbnail || undefined} style={{ width: "100%", maxHeight: "70vh", display: "block" }} />
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", py: 8 }}>
            <Film style={{ width: 48, height: 48, color: "#555" }} />
            <Typography fontSize={13} color="#777" sx={{ mt: 1.5 }}>No playback URL available</Typography>
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function PlaylistDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { getToken } = useAuth();
  const router = useRouter();

  const [playlist, setPlaylist] = useState<PlaylistDetail | null>(null);
  const [vmap, setVmap] = useState<Map<string, VideoInfo>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pv, setPv] = useState<VideoInfo | null>(null);
  const [pvOpen, setPvOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const token = await getApiToken(getToken as GetTokenFn);
      if (!token) return;
      const data = await getPlaylist(token, Number(id));
      setPlaylist(data);
      const ids = data.videos.map((v) => v.video_id);
      if (ids.length > 0) {
        const docs = await getVideosByIds(ids);
        const m = new Map<string, VideoInfo>();
        for (const doc of docs) { const info = extractVideoInfo(doc); if (info.video_id) m.set(info.video_id, info); }
        setVmap(m);
      }
      setError("");
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to load playlist"); }
    finally { setLoading(false); }
  }, [getToken, id]);

  useEffect(() => { load(); }, [load]);

  const remove = async (vid: string) => {
    try {
      const token = await getApiToken(getToken as GetTokenFn);
      if (!token || !playlist) return;
      await removeVideoFromPlaylist(token, playlist.id, vid);
      setPlaylist((p) => p ? { ...p, videos: p.videos.filter((v) => v.video_id !== vid) } : p);
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to remove video"); }
  };

  if (loading) return <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}><CircularProgress size={28} sx={{ color: "#4D8AFF" }} /></Box>;
  if (!playlist) return <Alert severity="error">Playlist not found</Alert>;

  return (
    <Box>
      <Button startIcon={<ArrowLeft style={{ width: 15, height: 15 }} />} onClick={() => router.push("/dashboard/playlists")} sx={{ textTransform: "none", color: "#6b7280", mb: 1.5, fontSize: 13, p: 0.5 }}>
        Back
      </Button>

      <Box sx={{ mb: 2 }}>
        <Typography fontSize={18} fontWeight={700} color="#111827">{playlist.title}</Typography>
        {playlist.description && <Typography fontSize={13} color="text.secondary">{playlist.description}</Typography>}
        <Typography fontSize={12} color="text.secondary" sx={{ mt: 0.25 }}>{playlist.videos.length} video{playlist.videos.length !== 1 ? "s" : ""}</Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 1.5, py: 0, fontSize: 13 }}>{error}</Alert>}

      {playlist.videos.length === 0 ? (
        <Box sx={{ textAlign: "center", py: 6, border: "1px dashed #d1d5db", borderRadius: 2 }}>
          <Film style={{ width: 36, height: 36, color: "#9ca3af", margin: "0 auto 8px" }} />
          <Typography fontSize={13} color="text.secondary">No videos yet. Use the search assistant to add some.</Typography>
        </Box>
      ) : (
        <Grid container spacing={1.5}>
          {playlist.videos.map((item) => {
            const info = vmap.get(item.video_id);
            const title = info?.title ?? item.video_id;
            const hasThumb = !!info?.thumbnail;
            const hasPlay = !!info?.playUrl;
            const hasDl = !!info?.downloadUrl;

            return (
              <Grid size={{ xs: 6, sm: 4, md: 3 }} key={item.id}>
                <Card variant="outlined" sx={{ borderRadius: 1.5, overflow: "hidden", height: "100%", display: "flex", flexDirection: "column", transition: "box-shadow 0.15s", "&:hover": { boxShadow: "0 2px 12px rgba(0,0,0,0.07)" } }}>
                  {/* Thumbnail area */}
                  <Box
                    sx={{ position: "relative", bgcolor: "#f3f4f6", cursor: hasPlay ? "pointer" : "default", "&:hover .ov": { opacity: 1 } }}
                    onClick={() => { if (info && hasPlay) { setPv(info); setPvOpen(true); } }}
                  >
                    {hasThumb ? (
                      <CardMedia component="img" image={info!.thumbnail} alt={title} sx={{ height: 120, objectFit: "cover" }} />
                    ) : (
                      <Box sx={{ height: 120, display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <Film style={{ width: 32, height: 32, color: "#d1d5db" }} />
                      </Box>
                    )}
                    {info?.durationFormatted && (
                      <Box sx={{ position: "absolute", bottom: 4, right: 4, bgcolor: "rgba(0,0,0,0.72)", color: "white", fontSize: 10, fontWeight: 700, px: 0.75, py: 0.15, borderRadius: 0.5, lineHeight: 1.5 }}>
                        {info.durationFormatted}
                      </Box>
                    )}
                    {hasPlay && (
                      <Box className="ov" sx={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "rgba(0,0,0,0.3)", opacity: 0, transition: "opacity 0.15s" }}>
                        <Box sx={{ width: 36, height: 36, borderRadius: "50%", bgcolor: "rgba(255,255,255,0.9)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                          <Play style={{ width: 18, height: 18, color: "#111", marginLeft: 2 }} />
                        </Box>
                      </Box>
                    )}
                  </Box>

                  {/* Info area */}
                  <Box sx={{ flex: 1, display: "flex", flexDirection: "column", p: 1, gap: 0.25 }}>
                    <Typography fontSize={12} fontWeight={600} color="#111827" noWrap title={title}>{title}</Typography>
                    {info?.owner && <Typography fontSize={10} color="text.secondary" noWrap>{info.owner}</Typography>}
                    {info?.description && <Typography fontSize={10} color="text.secondary" sx={{ display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden", lineHeight: 1.35 }}>{info.description}</Typography>}

                    {/* Actions */}
                    <Box sx={{ mt: "auto", display: "flex", gap: 0.5, pt: 0.75 }}>
                      {hasPlay && (
                        <Tooltip title="Play">
                          <IconButton size="small" onClick={() => { if (info) { setPv(info); setPvOpen(true); } }} sx={{ bgcolor: "#111827", color: "white", width: 26, height: 26, "&:hover": { bgcolor: "#374151" } }}>
                            <Play style={{ width: 13, height: 13, marginLeft: 1 }} />
                          </IconButton>
                        </Tooltip>
                      )}
                      {hasDl && (
                        <Tooltip title="Download">
                          <IconButton size="small" component="a" href={info!.downloadUrl} target="_blank" rel="noopener noreferrer" sx={{ border: "1px solid #e5e7eb", width: 26, height: 26, color: "#374151", "&:hover": { bgcolor: "#f9fafb" } }}>
                            <Download style={{ width: 13, height: 13 }} />
                          </IconButton>
                        </Tooltip>
                      )}
                      <Tooltip title="Remove">
                        <IconButton size="small" onClick={() => remove(item.video_id)} sx={{ marginLeft: "auto", width: 26, height: 26, color: "#ef4444", border: "1px solid #fecaca", "&:hover": { bgcolor: "#fef2f2" } }}>
                          <Trash2 style={{ width: 12, height: 12 }} />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Box>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}

      <PlayerDialog video={pv} open={pvOpen} onClose={() => setPvOpen(false)} />
    </Box>
  );
}
