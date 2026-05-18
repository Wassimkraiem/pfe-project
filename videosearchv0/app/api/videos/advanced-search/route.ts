import { NextRequest, NextResponse } from 'next/server';

const VIDEOS_API_URL =
	process.env.VIDEOS_API_URL ||
	process.env.NEXT_PUBLIC_VIDEOS_API_URL ||
	'http://localhost:5000';

const VIDEOS_API_KEY =
	process.env.VIDEOS_API_KEY ||
	process.env.NEXT_PUBLIC_VIDEOS_API_KEY ||
	'key1';

export async function POST(request: NextRequest) {
	try {
		const body = await request.json();
		const response = await fetch(
			`${VIDEOS_API_URL.replace(/\/$/, '')}/api/videos/advanced-search`,
			{
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-API-KEY': VIDEOS_API_KEY,
				},
				body: JSON.stringify(body),
				cache: 'no-store',
			}
		);

		const text = await response.text();
		return new NextResponse(text, {
			status: response.status,
			headers: { 'Content-Type': 'application/json' },
		});
	} catch {
		return NextResponse.json(
			{ error: 'Failed to reach advanced search service' },
			{ status: 502 }
		);
	}
}
