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
			`${VIDEOS_API_URL.replace(/\/$/, '')}/api/videos/query?offset=0&limit=1`,
			{
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-API-KEY': VIDEOS_API_KEY,
				},
				body: JSON.stringify(body),
			}
		);

		const text = await response.text();
		return new NextResponse(text, {
			status: response.status,
			headers: { 'Content-Type': 'application/json' },
		});
	} catch {
		return NextResponse.json(
			{ error: 'Failed to query video service' },
			{ status: 502 }
		);
	}
}
