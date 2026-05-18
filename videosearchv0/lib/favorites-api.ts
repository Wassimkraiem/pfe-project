const AR_API_BASE_URL =
	typeof process !== 'undefined'
		? process.env.NEXT_PUBLIC_AR_API_URL ?? 'http://localhost:8000'
		: 'http://localhost:8000';

type ArEnvelope<T> = {
	status_code: number;
	message: string;
	data: T;
};

export async function addFavorite(
	token: string,
	payload: { video_id: string; video_title?: string; thumbnail_url?: string }
): Promise<void> {
	const res = await fetch(`${AR_API_BASE_URL}/favorites`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify(payload),
	});
	if (!res.ok) {
		const json = (await res.json()) as ArEnvelope<unknown>;
		// 409 means already favorited — treat as success
		if (res.status === 409) return;
		throw new Error(json.message ?? `Request failed: ${res.status}`);
	}
}

export async function removeFavorite(token: string, videoId: string): Promise<void> {
	const res = await fetch(
		`${AR_API_BASE_URL}/favorites/${encodeURIComponent(videoId)}`,
		{
			method: 'DELETE',
			headers: { Authorization: `Bearer ${token}` },
		}
	);
	if (!res.ok) {
		const json = (await res.json()) as ArEnvelope<unknown>;
		throw new Error(json.message ?? `Request failed: ${res.status}`);
	}
}

export async function getFavoritedIds(token: string): Promise<string[]> {
	const res = await fetch(`${AR_API_BASE_URL}/favorites/ids`, {
		headers: { Authorization: `Bearer ${token}` },
	});
	const json = (await res.json()) as ArEnvelope<{ video_ids: string[] }>;
	if (!res.ok) {
		throw new Error(json.message ?? `Request failed: ${res.status}`);
	}
	return json.data.video_ids;
}
