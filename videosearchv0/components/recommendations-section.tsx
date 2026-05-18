'use client';

import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '@clerk/nextjs';

import { VideoCard } from '@/components/video-card';
import { formatVideoData } from '@/lib/utils';
import {
	getRecommendations,
	ingestRecommendationClickEvent,
	type RecommendationItem,
} from '@/lib/recommendations-api';

export function RecommendationsSection() {
	const { isLoaded, isSignedIn, getToken } = useAuth();
	const [videos, setVideos] = useState<any[]>([]);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState('');

	const toRecommendationVideos = (items: RecommendationItem[]) =>
		items
			.map((item) =>
				formatVideoData({
					...(item?.document || {}),
					video_id:
						typeof item?.video_id === 'string'
							? item.video_id
							: (item?.document as any)?.video_id,
				})
			)
			.filter(Boolean);

	const fetchTrendingFallback = async () => {
		try {
			const res = await axios.post(
				'/api/videos/advanced-search',
				{
					query: '',
					filters: {},
					sort: { by: 'views', order: 'desc' },
					pagination: { offset: 0, limit: 10 },
				},
				{ headers: { 'Content-Type': 'application/json' } }
			);
			const payload = res.data?.data || {};
			const items = Array.isArray(payload.items) ? payload.items : [];
			const formatted = items
				.map((item: any) =>
					formatVideoData({
						...(item?.document || {}),
						video_id: item?.video_id || item?.document?.video_id,
					})
				)
				.filter(Boolean);
			setVideos(formatted);
		} catch {
			setVideos([]);
		}
	};

	const loadRecommendations = useCallback(async () => {
		if (!isLoaded || !isSignedIn) return;

		try {
			setLoading(true);
			setError('');
			const token = await getToken();
			if (!token) return;
			const data = await getRecommendations(token, { limit: 10, refresh: false });
			const formatted = toRecommendationVideos(data.items || []);
			if (formatted.length === 0) {
				await fetchTrendingFallback();
			} else {
				setVideos(formatted);
			}
		} catch {
			setError('Could not load recommendations');
			await fetchTrendingFallback();
		} finally {
			setLoading(false);
		}
	}, [getToken, isLoaded, isSignedIn]);

	const trackRecommendationClick = useCallback(
		async (video: any) => {
			if (!isLoaded || !isSignedIn) return;
			try {
				const token = await getToken();
				if (!token) return;
				const categoryValue = video?.category;
				const categoriesPayload = Array.isArray(categoryValue)
					? categoryValue.filter((item) => typeof item === 'string')
					: typeof categoryValue === 'string' && categoryValue
					? [categoryValue]
					: [];
				await ingestRecommendationClickEvent(token, {
					video_id: video?.id,
					event_type: 'click',
					event_context: {
						categories: categoriesPayload,
						tags: Array.isArray(video?.tags) ? video.tags : [],
					},
				});
			} catch (err) {
				console.error('Failed to ingest recommendation click event:', err);
			}
		},
		[getToken, isLoaded, isSignedIn]
	);

	useEffect(() => {
		void loadRecommendations();
	}, [loadRecommendations]);

	if (!isLoaded || !isSignedIn) return null;

	return (
		<section className='space-y-8'>
			<div className='text-center space-y-4'>
				<h2 className='text-3xl font-bold tracking-tight'>Recommended for You</h2>
				<p className='text-muted-foreground text-lg max-w-2xl mx-auto'>
					Personalized picks based on your recent activity
				</p>
			</div>

			{loading && (
				<div className='text-center py-8 text-sm text-muted-foreground'>
					Loading recommendations...
				</div>
			)}

			{videos.length > 0 ? (
				<div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'>
					{videos.slice(0, 8).map((video) => (
						<VideoCard
							key={`home-rec-${video.id}`}
							video={video}
							onOpen={trackRecommendationClick}
						/>
					))}
				</div>
			) : (
				!loading && (
					<div className='text-center py-8 text-sm text-muted-foreground'>
						{error || 'No recommendations yet.'}
					</div>
				)
			)}
		</section>
	);
}
