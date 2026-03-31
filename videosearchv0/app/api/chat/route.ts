import { NextRequest, NextResponse } from 'next/server';

const CHAT_API_URL =
	process.env.CHAT_API_URL ||
	process.env.NEXT_PUBLIC_CHAT_API_URL ||
	'http://localhost:8003/api/v1/chat';

const CHAT_API_KEY =
	process.env.CHAT_API_KEY ||
	process.env.NEXT_PUBLIC_CHAT_API_KEY ||
	'change-me';

export async function POST(request: NextRequest) {
	try {
		const body = await request.json();

		const response = await fetch(CHAT_API_URL, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'x-api-key': CHAT_API_KEY,
			},
			body: JSON.stringify(body),
		});

		const text = await response.text();
		return new NextResponse(text, {
			status: response.status,
			headers: { 'Content-Type': 'application/json' },
		});
	} catch (error) {
		return NextResponse.json(
			{ error: 'Failed to reach chat service' },
			{ status: 502 }
		);
	}
}
