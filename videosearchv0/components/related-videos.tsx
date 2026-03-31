'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { VideoCard } from '@/components/video-card';
import { formatVideoData } from '@/lib/utils';
import axios from 'axios';

interface RelatedVideosProps {
	category: string;
	currentVideoId: string;
}

export function RelatedVideos({
	category,
	currentVideoId,
}: RelatedVideosProps) {
	const [relatedVideos, setRelatedVideos] = useState<any[]>([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		async function fetchRelatedVideos() {
			setLoading(true);
			try {
				const res = await axios.post(
					'http://localhost:5000/api/videos/vsearch',
					{
						query: category,
						k: 6,
					},
					{ headers: { 'x-api-key': 'key1' } }
				);

				const documents = res.data?.data?.documents;

				if (!documents || documents.length === 0) {
					setRelatedVideos([]);
					return;
				}

				// Filter out the current video and format
				const formattedVideos = documents
					.filter((doc: any) => doc.video_id !== currentVideoId)
					.map((doc: any) => formatVideoData(doc))
					.slice(0, 5);

				setRelatedVideos(formattedVideos);
			} catch (error) {
				console.error('Fetch error:', error);
				setRelatedVideos([]);
			} finally {
				setLoading(false);
			}
		}

		fetchRelatedVideos();
	}, [category, currentVideoId]); // Refetch when these change

	return (
		<Card>
			<CardHeader>
				<CardTitle>Related Videos</CardTitle>
			</CardHeader>
			<CardContent className='space-y-4'>
				{loading ? (
					<p className='text-muted-foreground'>Loading...</p>
				) : relatedVideos && relatedVideos.length > 0 ? (
					relatedVideos.map((video) => (
						<div key={video.id} className='scale-90 origin-top-left'>
							<VideoCard video={video} />
						</div>
					))
				) : (
					<p className='text-muted-foreground'>No related videos found.</p>
				)}
			</CardContent>
		</Card>
	);
}
