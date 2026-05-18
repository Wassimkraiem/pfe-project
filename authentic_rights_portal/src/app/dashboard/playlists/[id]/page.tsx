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
    <Box sx={{ pb: 2 }}>
      <Button
        startIcon={<ArrowLeft style={{ width: 15, height: 15 }} />}
        onClick={() => router.push("/dashboard/playlists")}
        sx={{ textTransform: "none", color: "#6b7280", mb: 1.5, fontSize: 13, p: 0.5 }}
      >
        Back
      </Button>

      <Box
        sx={{
          mb: 2.5,
          p: { xs: 1.75, sm: 2.25 },
          borderRadius: 3,
          background: "linear-gradient(135deg, #111827 0%, #1e3a8a 55%, #1d4ed8 100%)",
          color: "white",
          boxShadow: "0 14px 40px rgba(30, 58, 138, 0.24)",
        }}
      >
        <Typography fontSize={12} fontWeight={600} sx={{ opacity: 0.72, letterSpacing: "0.08em", textTransform: "uppercase", mb: 0.5 }}>
          Playlist
        </Typography>
        <Typography fontSize={{ xs: 20, sm: 24 }} fontWeight={800} sx={{ lineHeight: 1.2 }}>
          {playlist.title}
        </Typography>
        {playlist.description && (
          <Typography fontSize={13} sx={{ mt: 0.8, opacity: 0.9, maxWidth: 740 }}>
            {playlist.description}
          </Typography>
        )}
        <Box sx={{ display: "flex", gap: 0.8, flexWrap: "wrap", mt: 1.3 }}>
          <Chip
            label={`${playlist.videos.length} video${playlist.videos.length !== 1 ? "s" : ""}`}
            size="small"
            sx={{ bgcolor: "rgba(255,255,255,0.18)", color: "white", fontWeight: 600, borderRadius: 2 }}
          />
          <Chip
            label="Grid preview"
            size="small"
            sx={{ bgcolor: "rgba(255,255,255,0.12)", color: "white", borderRadius: 2 }}
          />
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 1.5, py: 0, fontSize: 13 }}>{error}</Alert>}

      {playlist.videos.length === 0 ? (
        <Box
          sx={{
            textAlign: "center",
            py: 7,
            border: "1px dashed #d1d5db",
            borderRadius: 3,
            background:
              "radial-gradient(circle at top, rgba(59,130,246,0.12), rgba(255,255,255,0) 58%), #fafafa",
          }}
        >
          <Box
            sx={{
              width: 54,
              height: 54,
              borderRadius: "50%",
              bgcolor: "rgba(17,24,39,0.07)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              mx: "auto",
              mb: 1,
            }}
          >
            <Film style={{ width: 26, height: 26, color: "#6b7280" }} />
          </Box>
          <Typography fontSize={15} fontWeight={700} color="#111827">
            This playlist is empty
          </Typography>
          <Typography fontSize={13} color="text.secondary" sx={{ mt: 0.5 }}>
            Use the search assistant to add videos, then preview and manage them here.
          </Typography>
        </Box>
      ) : (
        <Box sx={{ maxWidth: 1160, mx: "auto" }}>
          <Grid container spacing={2}>
          {playlist.videos.map((item) => {
            const info = vmap.get(item.video_id);
            const title = info?.title ?? item.video_id;
            const hasThumb = !!info?.thumbnail;
            const hasPlay = !!info?.playUrl;
            const hasDl = !!info?.downloadUrl;

            return (
              <Grid size={{ xs: 6, sm: 4, md: 4, lg: 3 }} key={item.id}>
                <Card
                  variant="outlined"
                  sx={{
                    borderRadius: 3,
                    overflow: "hidden",
                    height: "100%",
                    display: "flex",
                    flexDirection: "column",
                    borderColor: "#e5e7eb",
                    boxShadow: "0 10px 28px rgba(15, 23, 42, 0.07)",
                    transition: "transform 0.2s, box-shadow 0.2s, border-color 0.2s",
                    "&:hover": {
                      transform: "translateY(-3px)",
                      borderColor: "#bfdbfe",
                      boxShadow: "0 18px 34px rgba(37, 99, 235, 0.16)",
                    },
                  }}
                >
                  <Box
                    sx={{
                      position: "relative",
                      bgcolor: "#f3f4f6",
                      cursor: hasPlay ? "pointer" : "default",
                      "&:hover .ov": { opacity: 1 },
                    }}
                    onClick={() => { if (info && hasPlay) { setPv(info); setPvOpen(true); } }}
                  >
                    {hasThumb ? (
                      <CardMedia component="img" image={info!.thumbnail} alt={title} sx={{ height: 152, objectFit: "cover" }} />
                    ) : (
                      <Box sx={{ height: 152, display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <Film style={{ width: 32, height: 32, color: "#d1d5db" }} />
                      </Box>
                    )}
                    <Box
                      sx={{
                        position: "absolute",
                        inset: 0,
                        background: "linear-gradient(180deg, rgba(0,0,0,0) 36%, rgba(0,0,0,0.72) 100%)",
                        pointerEvents: "none",
                      }}
                    />
                    <Typography
                      fontSize={11}
                      fontWeight={600}
                      color="white"
                      noWrap
                      title={title}
                      sx={{ position: "absolute", left: 8, right: 8, bottom: 8 }}
                    >
                      {title}
                    </Typography>
                    {info?.durationFormatted && (
                      <Box
                        sx={{
                          position: "absolute",
                          top: 8,
                          right: 8,
                          bgcolor: "rgba(17,24,39,0.82)",
                          color: "white",
                          fontSize: 10,
                          fontWeight: 700,
                          px: 0.8,
                          py: 0.25,
                          borderRadius: 1,
                          lineHeight: 1.5,
                        }}
                      >
                        {info.durationFormatted}
                      </Box>
                    )}
                    {hasPlay && (
                      <Box className="ov" sx={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "rgba(0,0,0,0.36)", opacity: 0, transition: "opacity 0.15s" }}>
                        <Box sx={{ width: 42, height: 42, borderRadius: "50%", bgcolor: "rgba(255,255,255,0.94)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 22px rgba(0,0,0,0.35)" }}>
                          <Play style={{ width: 18, height: 18, color: "#111", marginLeft: 2 }} />
                        </Box>
                      </Box>
                    )}
                  </Box>

                  <Box sx={{ flex: 1, display: "flex", flexDirection: "column", p: 1.1, gap: 0.55 }}>
                    {info?.owner && <Typography fontSize={11} color="#374151" noWrap>{info.owner}</Typography>}
                    {info?.description && (
                      <Typography
                        fontSize={10.5}
                        color="text.secondary"
                        sx={{
                          display: "-webkit-box",
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: "vertical",
                          overflow: "hidden",
                          lineHeight: 1.35,
                          minHeight: 28,
                        }}
                      >
                        {info.description}
                      </Typography>
                    )}
                    {info?.dimensions && (
                      <Chip
                        label={info.dimensions}
                        size="small"
                        sx={{
                          width: "fit-content",
                          maxWidth: "100%",
                          height: 20,
                          fontSize: 10,
                          bgcolor: "#f3f4f6",
                          color: "#4b5563",
                          borderRadius: 1.2,
                        }}
                      />
                    )}

                    <Box sx={{ mt: "auto", display: "flex", gap: 0.5, pt: 0.6 }}>
                      {hasPlay && (
                        <Tooltip title="Play">
                          <IconButton size="small" onClick={() => { if (info) { setPv(info); setPvOpen(true); } }} sx={{ bgcolor: "#111827", color: "white", width: 28, height: 28, "&:hover": { bgcolor: "#1f2937" } }}>
                            <Play style={{ width: 13, height: 13, marginLeft: 1 }} />
                          </IconButton>
                        </Tooltip>
                      )}
                      {hasDl && (
                        <Tooltip title="Download">
                          <IconButton size="small" component="a" href={info!.downloadUrl} target="_blank" rel="noopener noreferrer" sx={{ border: "1px solid #d1d5db", width: 28, height: 28, color: "#374151", "&:hover": { bgcolor: "#f9fafb" } }}>
                            <Download style={{ width: 13, height: 13 }} />
                          </IconButton>
                        </Tooltip>
                      )}
                      <Tooltip title="Remove">
                        <IconButton size="small" onClick={() => remove(item.video_id)} sx={{ marginLeft: "auto", width: 28, height: 28, color: "#ef4444", border: "1px solid #fecaca", "&:hover": { bgcolor: "#fef2f2" } }}>
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
        </Box>
      )}

      <PlayerDialog video={pv} open={pvOpen} onClose={() => setPvOpen(false)} />
    </Box>
  );
}
