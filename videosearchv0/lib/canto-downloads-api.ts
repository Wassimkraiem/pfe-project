const AR_API_BASE_URL =
	typeof process !== 'undefined'
		? process.env.NEXT_PUBLIC_AR_API_URL ?? 'http://localhost:8000'
		: 'http://localhost:8000';

type ArEnvelope<T> = {
	status_code: number;
	message: string;
	data: T;
};

type DownloadSourceScope = 'browse' | 'detail';

export async function getCantoVideoDownloadUrl(
	token: string,
	videoId: string,
	options?: {
		sourceScope?: DownloadSourceScope;
		requestFilters?: Record<string, string>;
	}
): Promise<string> {
	const sourceScope = options?.sourceScope ?? 'browse';
	const params = new URLSearchParams({ source_scope: sourceScope });
	if (options?.requestFilters && Object.keys(options.requestFilters).length > 0) {
		params.set('request_filters', JSON.stringify(options.requestFilters));
	}

	const res = await fetch(
		`${AR_API_BASE_URL}/canto/videos/${encodeURIComponent(videoId)}/download?${params.toString()}`,
		{
			headers: {
				Authorization: `Bearer ${token}`,
			},
		}
	);
	const json = (await res.json()) as ArEnvelope<{ download_url: string }>;
	if (!res.ok) {
		throw new Error(json.message ?? `Request failed: ${res.status}`);
	}
	return json.data.download_url;
}
