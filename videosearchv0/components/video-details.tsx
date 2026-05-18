'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from '@/components/ui/card';
import {
	Play,
	Download,
	Share,
	Eye,
	Calendar,
	Clock,
	User,
	Tag,
	Monitor,
	HardDrive,
	Video,
	Volume2,
	Palette,
	MapPin,
	Award,
	Copy,
	CheckCircle,
	ExternalLink,
	Info,
	Loader2,
} from 'lucide-react';
import { VideoPlayer } from './video-player';
import { useAuth } from '@clerk/nextjs';
import { redirectToSignupPortal } from '@/lib/auth-portal';
import { AddToPlaylistButton } from './add-to-playlist-button';
import { getCantoVideoDownloadUrl } from '@/lib/canto-downloads-api';

interface VideoDetailsProps {
	video: VideoData | null;
	onBack?: () => void;
}

interface VideoData {
	id: string;
	title: string;
	description: string;
	thumbnail: string;
	duration: string;
	category: string;
	tags: string[];
	uploadDate: string;
	views: number;
	license: string;
	size: string;
	codec: string;
	dimensions: string;
	owner: string;
	approvalStatus: string;
	directUrlPreviewPlay: string;
	playUrl?: string;
	downloadUrl: string;
	detailUrl: string;
	bitRate: string;
	frameRate: string;
	aspectRatio: string;
	audioCodec: string;
	sampleRate: string;
	colorProfile: string;
	credit: string;
	location: string;
	originalData: any;
}

export function VideoDetails({ video, onBack }: VideoDetailsProps) {
	const { isSignedIn, isLoaded, getToken } = useAuth();
	const [linkCopied, setLinkCopied] = useState(false);
	const [rawDataCopied, setRawDataCopied] = useState(false);
	const [activeTab, setActiveTab] = useState('overview');
	const [watchTime, setWatchTime] = useState(0);
	const [isDownloading, setIsDownloading] = useState(false);

	const handleCopyLink = () => {
		navigator.clipboard.writeText(window.location.href);
		setLinkCopied(true);
		setTimeout(() => setLinkCopied(false), 2000);
	};

	const handleCopyRawData = () => {
		if (video?.originalData) {
			navigator.clipboard.writeText(
				JSON.stringify(video.originalData, null, 2)
			);
			setRawDataCopied(true);
			setTimeout(() => setRawDataCopied(false), 2000);
		}
	};

	const handleDownload = async () => {
		if (!video || isDownloading) return;

		try {
			setIsDownloading(true);
			const token = await getToken();
			if (!token) {
				throw new Error('Session expired. Please sign in again.');
			}
			const downloadUrl = await getCantoVideoDownloadUrl(token, video.id, {
				sourceScope: 'detail',
			});
			window.open(downloadUrl, '_blank', 'noopener,noreferrer');
		} catch (error) {
			console.error('Failed to download video', error);
			alert('Could not start the download.');
		} finally {
			setIsDownloading(false);
		}
	};

	const handleVideoEnd = useCallback(() => {
		console.log('Video playback ended');
	}, []);

	const handleTimeUpdate = useCallback((currentTime: number) => {
		setWatchTime(currentTime);
	}, []);

	const formatUploadDate = (dateString: string) => {
		return new Date(dateString).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
		});
	};

	const getWatchProgress = () => {
		if (!video || !watchTime) return 0;
		const durationInSeconds = parseDuration(video.duration);
		return durationInSeconds > 0 ? (watchTime / durationInSeconds) * 100 : 0;
	};

	const parseDuration = (duration: string) => {
		const parts = duration.split(':').map(Number);
		if (parts.length === 2) {
			return parts[0] * 60 + parts[1];
		} else if (parts.length === 3) {
			return parts[0] * 3600 + parts[1] * 60 + parts[2];
		}
		return 0;
	};

	if (!video) {
		return (
			<div className='flex justify-center items-center py-12'>
				<div className='text-center'>
					<div className='text-red-500 mb-4'>Video not found</div>
					{onBack && (
						<Button onClick={onBack} variant='outline'>
							Go Back
						</Button>
					)}
				</div>
			</div>
		);
	}

	const playbackUrl = video.directUrlPreviewPlay || video.playUrl;

	return (
		<div className='max-w-7xl mx-auto space-y-6'>
			{onBack && (
				<Button onClick={onBack} variant='outline' className='mb-4'>
					← Back to Results
				</Button>
			)}

			{/* Main video content - full width */}
			<div key={video.id} className='space-y-4'>
				{playbackUrl ? (
					<VideoPlayer
						video={{
							...video,
							playUrl: playbackUrl,
						}}
						autoplay={false}
						onVideoEnd={handleVideoEnd}
						onTimeUpdate={handleTimeUpdate}
					/>
				) : (
					<Card className='overflow-hidden'>
						<CardContent className='p-0'>
							<div className='relative aspect-video bg-black rounded-lg overflow-hidden'>
								<img
									src={video.thumbnail}
									alt={video.title}
									className='w-full h-full object-cover'
								/>
								<div className='absolute inset-0 flex items-center justify-center bg-black bg-opacity-50'>
									<div className='text-center text-white'>
										<Play className='h-16 w-16 mx-auto mb-2' />
										<p className='text-sm'>Video not available for playback</p>
									</div>
								</div>
							</div>
						</CardContent>
					</Card>
				)}

				<div className='space-y-4'>
					<div>
						<h1 className='text-3xl font-bold'>{video.title}</h1>
						<p className='text-muted-foreground mt-2 text-lg'>
							{video.description}
						</p>
					</div>

					<div className='flex flex-wrap items-center gap-4 text-sm text-muted-foreground'>
						<div className='flex items-center gap-1'>
							<Eye className='h-4 w-4' />
							<span>{video.views.toLocaleString()} views</span>
						</div>
						<div className='flex items-center gap-1'>
							<Calendar className='h-4 w-4' />
							<span>{formatUploadDate(video.uploadDate)}</span>
						</div>
						<div className='flex items-center gap-1'>
							<Clock className='h-4 w-4' />
							<span>{video.duration}</span>
						</div>
						<div className='flex items-center gap-1'>
							<User className='h-4 w-4' />
							<span>By {video.owner}</span>
						</div>
						{watchTime > 0 && (
							<div className='flex items-center gap-1'>
								<Play className='h-4 w-4' />
								<span>{getWatchProgress().toFixed(1)}% watched</span>
							</div>
						)}
					</div>

					<div className='flex flex-wrap gap-2'>
						<Badge variant='outline'>{video.category}</Badge>
						{video.tags.map((tag, index) => (
							<Badge key={index} variant='secondary'>
								<Tag className='h-3 w-3 mr-1' />
								{tag}
							</Badge>
						))}
					</div>

					{/* Action buttons - conditional rendering based on auth */}
					{isLoaded && (
						<div className='flex flex-wrap gap-3 pt-2'>
							{isSignedIn ? (
								<>
									<Button
										variant='outline'
										onClick={handleDownload}
										disabled={isDownloading}
									>
										{isDownloading ? (
											<Loader2 className='h-4 w-4 mr-2 animate-spin' />
										) : (
											<Download className='h-4 w-4 mr-2' />
										)}
										{isDownloading ? 'Preparing...' : 'Download'}
									</Button>
									<AddToPlaylistButton
										videoId={video.id}
										videoTitle={video.title}
									/>

									<Button variant='outline' onClick={handleCopyLink}>
										{linkCopied ? (
											<CheckCircle className='h-4 w-4 mr-2' />
										) : (
											<Share className='h-4 w-4 mr-2' />
										)}
										{linkCopied ? 'Copied!' : 'Share'}
									</Button>

									{video.detailUrl && (
										<Button variant='outline' asChild>
											<a
												href={video.detailUrl}
												target='_blank'
												rel='noopener noreferrer'
											>
												<ExternalLink className='h-4 w-4 mr-2' />
												View Original
											</a>
										</Button>
									)}
								</>
							) : (
								<div className='w-full rounded-lg border border-dashed p-4'>
									<div className='text-center'>
										<p className='text-sm font-medium mb-3'>
											Create your BVIRAL account to unlock downloads and playlists.
										</p>
										<Button
											variant='default'
											onClick={redirectToSignupPortal}
											className='whitespace-nowrap'
										>
											Sign Up
										</Button>
									</div>
								</div>
							)}
						</div>
					)}
				</div>
			</div>

			{/* Tabs section */}
			<Tabs value={activeTab} onValueChange={setActiveTab} className='w-full'>
				<TabsList className='grid w-full grid-cols-4'>
					<TabsTrigger value='overview'>Overview</TabsTrigger>
					<TabsTrigger value='technical'>Technical</TabsTrigger>
					<TabsTrigger value='metadata'>Metadata</TabsTrigger>
					<TabsTrigger value='raw'>Raw Data</TabsTrigger>
				</TabsList>

				<TabsContent value='overview' className='space-y-4'>
					<div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
						<Card>
							<CardHeader>
								<CardTitle className='flex items-center gap-2'>
									<Info className='h-5 w-5' />
									Video Information
								</CardTitle>
							</CardHeader>
							<CardContent className='space-y-3'>
								<div className='grid grid-cols-2 gap-4'>
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											Duration
										</label>
										<p className='text-sm'>{video.duration}</p>
									</div>
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											Category
										</label>
										<p className='text-sm'>{video.category}</p>
									</div>
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											Upload Date
										</label>
										<p className='text-sm'>
											{formatUploadDate(video.uploadDate)}
										</p>
									</div>
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											Views
										</label>
										<p className='text-sm'>{video.views.toLocaleString()}</p>
									</div>
								</div>
							</CardContent>
						</Card>

						<Card>
							<CardHeader>
								<CardTitle className='flex items-center gap-2'>
									<User className='h-5 w-5' />
									Creator Information
								</CardTitle>
							</CardHeader>
							<CardContent className='space-y-3'>
								<div>
									<label className='text-sm font-medium text-muted-foreground'>
										Owner
									</label>
									<p className='text-sm'>{video.owner}</p>
								</div>
								{video.credit && (
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											Credit
										</label>
										<p className='text-sm'>{video.credit}</p>
									</div>
								)}
								{video.location && (
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											Location
										</label>
										<p className='text-sm flex items-center gap-1'>
											<MapPin className='h-3 w-3' />
											{video.location}
										</p>
									</div>
								)}
								<div>
									<label className='text-sm font-medium text-muted-foreground'>
										Status
									</label>
									<p className='text-sm flex items-center gap-1'>
										<Award className='h-3 w-3' />
										{video.approvalStatus}
									</p>
								</div>
							</CardContent>
						</Card>
					</div>
				</TabsContent>

				<TabsContent value='technical' className='space-y-4'>
					<div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
						<Card>
							<CardHeader>
								<CardTitle className='flex items-center gap-2'>
									<Video className='h-5 w-5' />
									Video Specifications
								</CardTitle>
							</CardHeader>
							<CardContent className='space-y-3'>
								<div className='grid grid-cols-2 gap-4'>
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											Resolution
										</label>
										<p className='text-sm flex items-center gap-1'>
											<Monitor className='h-3 w-3' />
											{video.dimensions}
										</p>
									</div>
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											Aspect Ratio
										</label>
										<p className='text-sm'>{video.aspectRatio}</p>
									</div>
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											Codec
										</label>
										<p className='text-sm'>{video.codec}</p>
									</div>
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											Frame Rate
										</label>
										<p className='text-sm'>{video.frameRate}</p>
									</div>
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											Bit Rate
										</label>
										<p className='text-sm'>{video.bitRate}</p>
									</div>
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											Color Profile
										</label>
										<p className='text-sm flex items-center gap-1'>
											<Palette className='h-3 w-3' />
											{video.colorProfile}
										</p>
									</div>
								</div>
							</CardContent>
						</Card>

						<Card>
							<CardHeader>
								<CardTitle className='flex items-center gap-2'>
									<Volume2 className='h-5 w-5' />
									Audio & File Info
								</CardTitle>
							</CardHeader>
							<CardContent className='space-y-3'>
								<div className='grid grid-cols-2 gap-4'>
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											Audio Codec
										</label>
										<p className='text-sm'>{video.audioCodec}</p>
									</div>
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											Sample Rate
										</label>
										<p className='text-sm'>{video.sampleRate}</p>
									</div>
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											File Size
										</label>
										<p className='text-sm flex items-center gap-1'>
											<HardDrive className='h-3 w-3' />
											{video.size}
										</p>
									</div>
									<div>
										<label className='text-sm font-medium text-muted-foreground'>
											License
										</label>
										<p className='text-sm'>{video.license}</p>
									</div>
								</div>
							</CardContent>
						</Card>
					</div>
				</TabsContent>

				<TabsContent value='metadata' className='space-y-4'>
					<Card>
						<CardHeader>
							<CardTitle>All Metadata</CardTitle>
							<CardDescription>
								Complete metadata information extracted from the video file
							</CardDescription>
						</CardHeader>
						<CardContent>
							<div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
								{Object.entries({
									Title: video.title,
									Description: video.description,
									Owner: video.owner,
									Duration: video.duration,
									'Upload Date': formatUploadDate(video.uploadDate),
									Views: video.views.toLocaleString(),
									Category: video.category,
									'File Size': video.size,
									Resolution: video.dimensions,
									'Aspect Ratio': video.aspectRatio,
									'Video Codec': video.codec,
									'Frame Rate': video.frameRate,
									'Bit Rate': video.bitRate,
									'Audio Codec': video.audioCodec,
									'Sample Rate': video.sampleRate,
									'Color Profile': video.colorProfile,
									License: video.license,
									Status: video.approvalStatus,
									...(video.credit && { Credit: video.credit }),
									...(video.location && { Location: video.location }),
									...(watchTime > 0 && {
										'Watch Progress': `${getWatchProgress().toFixed(1)}%`,
										'Watch Time': `${Math.floor(watchTime / 60)}:${Math.floor(
											watchTime % 60
										)
											.toString()
											.padStart(2, '0')}`,
									}),
								}).map(([key, value]) => (
									<div key={key} className='space-y-1'>
										<label className='text-xs font-medium text-muted-foreground uppercase tracking-wide'>
											{key}
										</label>
										<p className='text-sm break-words'>{value || 'N/A'}</p>
									</div>
								))}
							</div>
						</CardContent>
					</Card>
				</TabsContent>

				<TabsContent value='raw' className='space-y-4'>
					<Card>
						<CardHeader>
							<CardTitle>Raw API Response</CardTitle>
							<CardDescription>
								Original data structure returned from the API
							</CardDescription>
						</CardHeader>
						<CardContent>
							<div className='relative'>
								<Button
									size='sm'
									variant='outline'
									className='absolute top-2 right-2 z-10'
									onClick={handleCopyRawData}
								>
									{rawDataCopied ? (
										<CheckCircle className='h-3 w-3' />
									) : (
										<Copy className='h-3 w-3' />
									)}
								</Button>
								<pre className='bg-muted p-4 rounded-lg text-xs overflow-auto max-h-96'>
									{JSON.stringify(video.originalData, null, 2)}
								</pre>
							</div>
						</CardContent>
					</Card>
				</TabsContent>
			</Tabs>

			{/* Viewing Statistics */}
			{watchTime > 0 && (
				<div className='space-y-4'>
					<h2 className='text-2xl font-bold'>Viewing Statistics</h2>
					<div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
						<Card>
							<CardHeader className='pb-3'>
								<CardTitle className='text-base'>Quick Info</CardTitle>
							</CardHeader>
							<CardContent className='space-y-2'>
								<div className='space-y-2'>
									<div className='flex justify-between'>
										<span className='text-sm text-muted-foreground'>
											Resolution
										</span>
										<span className='text-sm font-medium'>
											{video.dimensions}
										</span>
									</div>
									<div className='flex justify-between'>
										<span className='text-sm text-muted-foreground'>
											File Size
										</span>
										<span className='text-sm font-medium'>{video.size}</span>
									</div>
									<div className='flex justify-between'>
										<span className='text-sm text-muted-foreground'>
											Format
										</span>
										<span className='text-sm font-medium'>{video.codec}</span>
									</div>
									<div className='flex justify-between'>
										<span className='text-sm text-muted-foreground'>
											License
										</span>
										<span className='text-sm font-medium'>{video.license}</span>
									</div>
								</div>
							</CardContent>
						</Card>

						<Card>
							<CardHeader className='pb-3'>
								<CardTitle className='text-base'>Playback Progress</CardTitle>
							</CardHeader>
							<CardContent className='space-y-2'>
								<div className='space-y-2'>
									<div className='flex justify-between'>
										<span className='text-sm text-muted-foreground'>
											Current Time
										</span>
										<span className='text-sm font-medium'>
											{Math.floor(watchTime / 60)}:
											{Math.floor(watchTime % 60)
												.toString()
												.padStart(2, '0')}
										</span>
									</div>
									<div className='flex justify-between'>
										<span className='text-sm text-muted-foreground'>
											Progress
										</span>
										<span className='text-sm font-medium'>
											{getWatchProgress().toFixed(1)}%
										</span>
									</div>
									<div className='w-full bg-muted rounded-full h-2'>
										<div
											className='bg-primary h-2 rounded-full transition-all duration-300'
											style={{ width: `${getWatchProgress()}%` }}
										></div>
									</div>
								</div>
							</CardContent>
						</Card>
					</div>
				</div>
			)}
		</div>
	);
}
