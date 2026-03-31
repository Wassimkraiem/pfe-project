const AR_API_BASE_URL =
  typeof process !== "undefined"
    ? process.env.NEXT_PUBLIC_AR_API_URL ?? "http://localhost:8000"
    : "http://localhost:8000";

type ArEnvelope<T> = {
  status_code: number;
  message: string;
  data: T;
};

export type PlaylistSummary = {
  id: number;
  title: string;
  description: string | null;
  created_at: string;
  updated_at: string | null;
  video_count: number;
};

export type PlaylistDetail = PlaylistSummary & {
  videos: { id: number; video_id: string; position: number; created_at: string }[];
};

export async function getPlaylists(
  token: string,
): Promise<PlaylistSummary[]> {
  const res = await fetch(`${AR_API_BASE_URL}/playlists`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const json = (await res.json()) as ArEnvelope<PlaylistSummary[]>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function createPlaylist(
  token: string,
  payload: { title: string; description?: string; video_ids?: string[] },
): Promise<PlaylistSummary> {
  const res = await fetch(`${AR_API_BASE_URL}/playlists`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  const json = (await res.json()) as ArEnvelope<PlaylistSummary>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function addVideosToPlaylist(
  token: string,
  playlistId: number,
  videoIds: string[],
): Promise<PlaylistDetail> {
  const res = await fetch(`${AR_API_BASE_URL}/playlists/${playlistId}/videos`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ video_ids: videoIds }),
  });
  const json = (await res.json()) as ArEnvelope<PlaylistDetail>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}
