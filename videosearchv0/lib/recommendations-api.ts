const AR_API_BASE_URL =
	typeof process !== 'undefined'
		? process.env.NEXT_PUBLIC_AR_API_URL ?? 'http://localhost:8000'
		: 'http://localhost:8000';

type ArEnvelope<T> = {
	status_code: number;
	message: string;
	data: T;
};

export type RecommendationItem = {
	video_id: string;
	document: Record<string, unknown>;
	recommendation_score: number;
	source: string[];
};

type RecommendationResponse = {
	items: RecommendationItem[];
	total: number;
	generated_at: string;
	seed: {
		categories: string[];
		tags: string[];
		entities: string[];
		query_terms: string[];
	};
};

export async function ingestRecommendationSearchEvent(
	token: string,
	payload: {
		query: string;
		parsed_intent?: Record<string, unknown>;
	}
): Promise<void> {
	const res = await fetch(`${AR_API_BASE_URL}/recommendations/events/search`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify(payload),
	});
	if (!res.ok) {
		const json = (await res.json()) as ArEnvelope<unknown>;
		throw new Error(json.message ?? `Request failed: ${res.status}`);
	}
}

export async function ingestRecommendationClickEvent(
	token: string,
	payload: {
		video_id: string;
		event_type?: string;
		event_context?: Record<string, unknown>;
	}
): Promise<void> {
	const res = await fetch(`${AR_API_BASE_URL}/recommendations/events/click`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify(payload),
	});
	if (!res.ok) {
		const json = (await res.json()) as ArEnvelope<unknown>;
		throw new Error(json.message ?? `Request failed: ${res.status}`);
	}
}

export async function getRecommendations(
	token: string,
	params?: { limit?: number; refresh?: boolean }
): Promise<RecommendationResponse> {
	const limit = params?.limit ?? 10;
	const refresh = params?.refresh ?? false;
	const query = new URLSearchParams({
		limit: String(limit),
		refresh: String(refresh),
	});

	const res = await fetch(`${AR_API_BASE_URL}/recommendations?${query.toString()}`, {
		headers: { Authorization: `Bearer ${token}` },
	});
	const json = (await res.json()) as ArEnvelope<RecommendationResponse>;
	if (!res.ok) {
		throw new Error(json.message ?? `Request failed: ${res.status}`);
	}
	return json.data;
}
