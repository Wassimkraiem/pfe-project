'use client';

import { useEffect, useState } from 'react';
import { VideoCard } from '@/components/video-card';
import { Button } from '@/components/ui/button';
import { Library } from 'lucide-react';
import Link from 'next/link';
import axios from 'axios';
import { formatVideoData } from './../lib/utils';

const VIDEOS_TO_SHOW = 4;

export function LatestVideos() {
	const [videos, setVideos] = useState<any[]>([]);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState('');

	useEffect(() => {
		const fetchVideos = async () => {
			setLoading(true);
			setError('');
			try {
				const res = await axios.get(
					'http://localhost:5000/api/videos/getlatest',
					{
						headers: {
							'x-api-key': 'key1',
						},
					}
				);

				let videoData = res.data?.data?.videos || [];

				if (!Array.isArray(videoData)) {
					videoData = [videoData];
				}
				const formattedVideos = videoData.map(formatVideoData).filter(Boolean);

				setVideos(formattedVideos);
			} catch (err) {
				setError('Failed to fetch videos');
				console.error('API Error:', err);
			} finally {
				setLoading(false);
			}
		};

		fetchVideos();
	}, []);

	// Split videos into visible and hidden
	const visibleVideos = videos.slice(0, VIDEOS_TO_SHOW);
	const hiddenVideos = videos.slice(VIDEOS_TO_SHOW);
	const blurredPreviewVideos = hiddenVideos.slice(0, VIDEOS_TO_SHOW);

	if (loading) {
		return (
			<div className='flex justify-center items-center py-12'>
				<div className='text-lg'>Loading latest videos...</div>
			</div>
		);
	}

	if (error) {
		return (
			<div className='flex justify-center items-center py-12'>
				<div className='text-red-500'>{error}</div>
			</div>
		);
	}

	return (
		<div id='latest-videos' className='space-y-8'>
			{/* Visible Videos - Single Row */}
			<div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'>
				{visibleVideos.map((video, index) => (
					<VideoCard key={video.id || `video-${index}`} video={video} />
				))}
			</div>

			{/* Blurred Hidden Videos Section */}
			{hiddenVideos.length > 0 && (
				<div className='relative'>
					{/* Blurred videos grid */}
					<div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 blur-sm pointer-events-none opacity-60'>
						{blurredPreviewVideos.map((video, index) => (
							<VideoCard
								key={video.id || `video-hidden-${index}`}
								video={video}
							/>
						))}
					</div>

					{/* Overlay with gradient and button */}
					<div className='absolute inset-0 bg-gradient-to-b from-white/30 via-white/60 to-white/90 flex items-center justify-center'>
						<Link href='/search'>
							<Button
								size='lg'
								className='h-14 px-10 text-lg font-semibold shadow-lg hover:shadow-xl transition-all'
							>
								<Library className='mr-2 h-6 w-6' />
								Explore Full Library
							</Button>
						</Link>
					</div>
				</div>
			)}

			{/* Fallback button if no hidden videos */}
			{hiddenVideos.length === 0 && videos.length > 0 && (
				<div className='flex justify-center items-center pt-4'>
					<Link href='/search'>
						<Button variant='outline' size='lg' className='h-12 px-8 text-base'>
							<Library className='mr-2 h-5 w-5' />
							Explore Full Library
						</Button>
					</Link>
				</div>
			)}
		</div>
	);
}
