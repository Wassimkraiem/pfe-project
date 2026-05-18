'use client';

import { useState, useRef, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Clock, Eye, Download, Heart, Loader2, Volume2, VolumeX } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { AddToPlaylistButton } from '@/components/add-to-playlist-button';
import { useAuth } from '@clerk/nextjs';
import { getCantoVideoDownloadUrl } from '@/lib/canto-downloads-api';
import { addFavorite, removeFavorite } from '@/lib/favorites-api';
import { ingestRecommendationClickEvent } from '@/lib/recommendations-api';

interface Video {
	id: string;
	title: string;
	description: string;
	thumbnail: string;
	directUrlPreviewPlay: string; // The playable video URL for preview
	duration: string;
	category: string;
	tags: string[];
	uploadDate: string;
	views: number;
	license: string;
}

interface VideoCardProps {
	video: Video;
	onOpen?: (video: Video) => void;
	initialIsFavorited?: boolean;
}

export function VideoCard({ video, onOpen, initialIsFavorited = false }: VideoCardProps) {
	const { isLoaded, isSignedIn, getToken } = useAuth();
	const [isHovered, setIsHovered] = useState(false);
	const [isFavorited, setIsFavorited] = useState(initialIsFavorited);
	const [isFavoriting, setIsFavoriting] = useState(false);
	const [isPlaying, setIsPlaying] = useState(false);
	const [isMuted, setIsMuted] = useState(true);
	const [showVideo, setShowVideo] = useState(false);
	const [videoLoaded, setVideoLoaded] = useState(false);
	const [isDownloading, setIsDownloading] = useState(false);
	const videoRef = useRef<HTMLVideoElement>(null);
	const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

	// Preview settings
	const PREVIEW_START_TIME = 0; // Start from beginning (you can change this)
	const PREVIEW_DURATION = 5; // Show 15 seconds as preview

	const formatDate = (dateString: string) => {
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
		});
	};

	const formatViews = (views: number) => {
		if (views >= 1000000) {
			return `${(views / 1000000).toFixed(1)}M`;
		} else if (views >= 1000) {
			return `${(views / 1000).toFixed(1)}K`;
		}
		return views.toString();
	};

	const handleMouseEnter = () => {
		setIsHovered(true);

		// Show video preview using directUrlPreviewPlay
		if (video.directUrlPreviewPlay) {
			// Delay showing video to avoid flashing on quick hovers
			hoverTimeoutRef.current = setTimeout(() => {
				setShowVideo(true);
			}, 500); // 500ms delay
		}
	};

	const handleMouseLeave = () => {
		setIsHovered(false);
		setIsPlaying(false);
		setShowVideo(false);
		setVideoLoaded(false);

		if (hoverTimeoutRef.current) {
			clearTimeout(hoverTimeoutRef.current);
			hoverTimeoutRef.current = null;
		}

		// Pause and reset video
		if (videoRef.current) {
			videoRef.current.pause();
			videoRef.current.currentTime = PREVIEW_START_TIME;
		}
	};

	const toggleMute = (e: React.MouseEvent) => {
		e.preventDefault();
		e.stopPropagation();
		setIsMuted(!isMuted);
		if (videoRef.current) {
			videoRef.current.muted = !isMuted;
		}
	};

	// Play video when it's shown and ready.
	// With preload='none' the browser never starts loading until play() is called,
	// so readyState is always 0 and a canplay listener alone never fires.
	// Solution: call play() immediately — it triggers the load; canplay updates UI.
	useEffect(() => {
		if (!showVideo || !videoRef.current || !video.directUrlPreviewPlay) return;

		const videoElement = videoRef.current;

		const handleCanPlay = () => setVideoLoaded(true);
		const handleTimeUpdate = () => {
			if (videoElement.currentTime >= PREVIEW_START_TIME + PREVIEW_DURATION) {
				videoElement.currentTime = PREVIEW_START_TIME;
			}
		};

		videoElement.addEventListener('canplay', handleCanPlay);
		videoElement.addEventListener('timeupdate', handleTimeUpdate);
		videoElement.muted = isMuted;

		videoElement.play().then(() => {
			setIsPlaying(true);
		}).catch(() => {
			// Autoplay blocked or component unmounted before play resolved
		});

		return () => {
			videoElement.removeEventListener('canplay', handleCanPlay);
			videoElement.removeEventListener('timeupdate', handleTimeUpdate);
		};
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [showVideo]);

	// Cleanup timeout on unmount
	useEffect(() => {
		return () => {
			if (hoverTimeoutRef.current) {
				clearTimeout(hoverTimeoutRef.current);
			}
		};
	}, []);

	const handleFavoriteToggle = async (e: React.MouseEvent) => {
		e.preventDefault();
		e.stopPropagation();
		if (isFavoriting || !isLoaded || !isSignedIn) return;

		const next = !isFavorited;
		setIsFavorited(next);
		setIsFavoriting(true);
		try {
			const token = await getToken();
			if (!token) throw new Error('Not authenticated');
			if (next) {
				await addFavorite(token, {
					video_id: video.id,
					video_title: video.title,
					thumbnail_url: video.thumbnail,
				});
				ingestRecommendationClickEvent(token, {
					video_id: video.id,
					event_type: 'favorite',
					event_context: { source: 'video_card' },
				}).catch(() => {});
			} else {
				await removeFavorite(token, video.id);
			}
		} catch {
			setIsFavorited(!next);
		} finally {
			setIsFavoriting(false);
		}
	};

	const handleDownload = async (e: React.MouseEvent) => {
		e.preventDefault();
		e.stopPropagation();

		if (isDownloading) return;

		try {
			setIsDownloading(true);
			const token = await getToken();
			if (!token) {
				throw new Error('Session expired. Please sign in again.');
			}
			const downloadUrl = await getCantoVideoDownloadUrl(token, video.id, {
				sourceScope: 'browse',
			});
			window.open(downloadUrl, '_blank', 'noopener,noreferrer');
		} catch (error) {
			console.error('Failed to download video', error);
			alert('Could not start the download.');
		} finally {
			setIsDownloading(false);
		}
	};

	return (
		<div
			onMouseEnter={handleMouseEnter}
			onMouseLeave={handleMouseLeave}
			className='relative'
		>
			<Link
				href={`/video/${video.id}`}
				onClick={() => {
					onOpen?.(video);
				}}
			>
				<Card className='group overflow-hidden hover:shadow-lg transition-all duration-300'>
					<div className='relative aspect-video overflow-hidden'>
						{/* Thumbnail Image */}
						<div
							className={`absolute inset-0 transition-opacity duration-300 ${
								showVideo && videoLoaded ? 'opacity-0' : 'opacity-100'
							}`}
						>
							<Image
								src={video.thumbnail}
								alt={video.title}
								fill
								className='object-cover group-hover:scale-105 transition-transform duration-300'
							/>
						</div>

						{/* Video Preview - only mount on hover to avoid background metadata fetches */}
						{video.directUrlPreviewPlay && showVideo && (
							<div
								className={`absolute inset-0 transition-opacity duration-300 ${videoLoaded ? 'opacity-100' : 'opacity-0'}`}
							>
								<video
									ref={videoRef}
									className='w-full h-full object-cover'
									muted={isMuted}
									playsInline
									preload='none'
								>
									<source src={video.directUrlPreviewPlay} type='video/mp4' />
									<source src={video.directUrlPreviewPlay} type='video/webm' />
									<source src={video.directUrlPreviewPlay} type='video/ogg' />
								</video>
							</div>
						)}

						{/* Hover Overlay */}
						<div
							className={`absolute inset-0 bg-black/0 transition-colors duration-300 ${
								isHovered ? 'bg-black/10' : ''
							}`}
						/>

						{/* Video Controls (only show when video is playing) */}
						{showVideo && isPlaying && (
							<div className='absolute top-2 right-12'>
								<Button
									size='sm'
									variant='secondary'
									className='opacity-80 hover:opacity-100'
									onClick={toggleMute}
								>
									{isMuted ? (
										<VolumeX className='h-3 w-3' />
									) : (
										<Volume2 className='h-3 w-3' />
									)}
								</Button>
							</div>
						)}

						{/* Duration Badge */}
						<div className='absolute bottom-2 right-2 bg-black/80 text-white px-2 py-1 rounded text-sm flex items-center z-10'>
							<Clock className='h-3 w-3 mr-1' />
							{video.duration}
						</div>

						{/* Category Badge */}
						<Badge className='absolute top-2 left-2 z-10' variant='secondary'>
							{video.category}
						</Badge>

						{/* Favorite Button — top-right of thumbnail */}
						{isLoaded && isSignedIn && (
							<button
								onClick={handleFavoriteToggle}
								disabled={isFavoriting}
								title={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
								className={`group/fav absolute top-2 right-2 z-20 p-1.5 rounded-full transition-all duration-200 focus:outline-none
									${isFavorited
										? 'bg-rose-500/90 opacity-100'
										: 'bg-black/50 opacity-0 group-hover:opacity-100 hover:bg-black/70'
									}`}
							>
								{isFavoriting ? (
									<Loader2 className='h-3.5 w-3.5 animate-spin text-white' />
								) : (
									<Heart
										className={`h-3.5 w-3.5 transition-colors
											${isFavorited
												? 'fill-white text-white'
												: 'text-white group-hover/fav:fill-rose-400 group-hover/fav:text-rose-400'
											}`}
									/>
								)}
							</button>
						)}

						{/* Preview Indicator */}
						{video.directUrlPreviewPlay && showVideo && !videoLoaded && (
							<div className='absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-white/80 text-xs bg-black/60 px-2 py-1 rounded'>
								Loading preview...
							</div>
						)}

						{/* No Preview Available Indicator */}
						{!video.directUrlPreviewPlay && isHovered && (
							<div className='absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-white/80 text-xs bg-black/60 px-2 py-1 rounded'>
								No preview available
							</div>
						)}
					</div>

					<CardContent className='p-4 space-y-3'>
						<div className='space-y-2'>
							<h3 className='font-semibold line-clamp-2 group-hover:text-primary transition-colors'>
								{video.title}
							</h3>
							<p className='text-sm text-muted-foreground line-clamp-2'>
								{video.description}
							</p>
						</div>

						<div className='flex flex-wrap gap-1'>
							{video.tags.slice(0, 3).map((tag) => (
								<Badge key={tag} variant='outline' className='text-xs'>
									{tag}
								</Badge>
							))}
						</div>

						<div className='flex items-center justify-between text-sm text-muted-foreground'>
							<div className='flex items-center space-x-4'>
								<span className='flex items-center'>
									<Eye className='h-3 w-3 mr-1' />
									{formatViews(video.views)}
								</span>
								<span>{formatDate(video.uploadDate)}</span>
							</div>
						{isLoaded && isSignedIn && (
							<div className='flex items-center gap-1'>
								<div
									onClick={(e) => {
										e.preventDefault();
										e.stopPropagation();
									}}
								>
									<AddToPlaylistButton
										videoId={video.id}
										videoTitle={video.title}
										size='sm'
										variant='ghost'
										className='px-2'
									/>
								</div>
								<Button
									size='sm'
									variant='ghost'
									onClick={handleDownload}
									disabled={isDownloading}
								>
									{isDownloading ? (
										<Loader2 className='h-4 w-4 animate-spin' />
									) : (
										<Download className='h-4 w-4' />
									)}
								</Button>
							</div>
						)}
						</div>
					</CardContent>
				</Card>
			</Link>
		</div>
	);
}
