'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import {
	Play,
	Pause,
	Volume2,
	VolumeX,
	Maximize,
	Settings,
	Download,
	SkipBack,
	SkipForward,
	ExternalLink,
} from 'lucide-react';

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
	playUrl: string;
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

interface VideoPlayerProps {
	video: VideoData;
	autoplay?: boolean;
	onVideoEnd?: () => void;
	onTimeUpdate?: (currentTime: number, duration: number) => void;
}

export function VideoPlayer({
	video,
	autoplay = false,
	onVideoEnd,
	onTimeUpdate,
}: VideoPlayerProps) {
	const videoRef = useRef<HTMLVideoElement>(null);
	const onVideoEndRef = useRef(onVideoEnd);
	const onTimeUpdateRef = useRef(onTimeUpdate);
	const [isPlaying, setIsPlaying] = useState(false);
	const [currentTime, setCurrentTime] = useState(0);
	const [duration, setDuration] = useState(0);
	const [volume, setVolume] = useState(80);
	const [isMuted, setIsMuted] = useState(false);
	const [showControls, setShowControls] = useState(true);
	const [isLoading, setIsLoading] = useState(true);
	const [hasError, setHasError] = useState(false);
	const [isFullscreen, setIsFullscreen] = useState(false);
	const [buffered, setBuffered] = useState(0);
	const [playPromise, setPlayPromise] = useState<Promise<void> | null>(null);

	useEffect(() => {
		onVideoEndRef.current = onVideoEnd;
	}, [onVideoEnd]);

	useEffect(() => {
		onTimeUpdateRef.current = onTimeUpdate;
	}, [onTimeUpdate]);

	// Initialize video when component mounts or video changes
	useEffect(() => {
		const videoElement = videoRef.current;
		if (!videoElement) return;

		const handleLoadedMetadata = () => {
			setDuration(videoElement.duration);
			setIsLoading(false);
			setHasError(false);

			// Set initial volume
			videoElement.volume = volume / 100;

			if (autoplay) {
				// Use setTimeout to ensure the video is ready before autoplay
				setTimeout(() => {
					// Check if video is ready to play
					if (videoElement.readyState >= 3) {
						togglePlay();
					} else {
						// Wait for canplay event
						videoElement.addEventListener(
							'canplay',
							() => {
								togglePlay();
							},
							{ once: true }
						);
					}
				}, 100);
			}
		};

		const handleTimeUpdate = () => {
			if (videoElement) {
				setCurrentTime(videoElement.currentTime);
				onTimeUpdateRef.current?.(videoElement.currentTime, videoElement.duration);

				// Update buffered progress
				if (videoElement.buffered.length > 0) {
					const bufferedEnd = videoElement.buffered.end(
						videoElement.buffered.length - 1
					);
					const bufferedPercent = (bufferedEnd / videoElement.duration) * 100;
					setBuffered(bufferedPercent);
				}
			}
		};

		const handleEnded = () => {
			setIsPlaying(false);
			setPlayPromise(null);
			onVideoEndRef.current?.();
		};

		const handleError = () => {
			setIsLoading(false);
			setHasError(true);
			setIsPlaying(false);
			setPlayPromise(null);
			console.error('Video failed to load:', video.playUrl);
		};

		const handleLoadStart = () => {
			setIsLoading(true);
			setHasError(false);
		};

		const handleCanPlay = () => {
			setIsLoading(false);
		};

		const handleCanPlayThrough = () => {
			setIsLoading(false);
		};

		const handleWaiting = () => {
			if (isPlaying) {
				setIsLoading(true);
			}
		};

		const handlePlaying = () => {
			setIsLoading(false);
			setIsPlaying(true);
		};

		const handleLoadedData = () => {
			setIsLoading(false);
		};

		const handlePlay = () => {
			setIsPlaying(true);
		};

		const handlePause = () => {
			setIsPlaying(false);
			setPlayPromise(null);
		};

		// Add event listeners
		videoElement.addEventListener('loadedmetadata', handleLoadedMetadata);
		videoElement.addEventListener('timeupdate', handleTimeUpdate);
		videoElement.addEventListener('ended', handleEnded);
		videoElement.addEventListener('error', handleError);
		videoElement.addEventListener('loadstart', handleLoadStart);
		videoElement.addEventListener('canplay', handleCanPlay);
		videoElement.addEventListener('canplaythrough', handleCanPlayThrough);
		videoElement.addEventListener('waiting', handleWaiting);
		videoElement.addEventListener('playing', handlePlaying);
		videoElement.addEventListener('loadeddata', handleLoadedData);
		videoElement.addEventListener('play', handlePlay);
		videoElement.addEventListener('pause', handlePause);

		// Cleanup
		return () => {
			videoElement.removeEventListener('loadedmetadata', handleLoadedMetadata);
			videoElement.removeEventListener('timeupdate', handleTimeUpdate);
			videoElement.removeEventListener('ended', handleEnded);
			videoElement.removeEventListener('error', handleError);
			videoElement.removeEventListener('loadstart', handleLoadStart);
			videoElement.removeEventListener('canplay', handleCanPlay);
			videoElement.removeEventListener('canplaythrough', handleCanPlayThrough);
			videoElement.removeEventListener('waiting', handleWaiting);
			videoElement.removeEventListener('playing', handlePlaying);
			videoElement.removeEventListener('loadeddata', handleLoadedData);
			videoElement.removeEventListener('play', handlePlay);
			videoElement.removeEventListener('pause', handlePause);

			// Clean up any pending play promise
			if (playPromise) {
				playPromise.catch(() => {
					// Ignore any errors from cleanup
				});
			}
		};
	}, [video.playUrl, autoplay]);

	useEffect(() => {
		const videoElement = videoRef.current;
		if (!videoElement) return;
		videoElement.volume = volume / 100;
	}, [volume]);

	const togglePlay = async () => {
		const videoElement = videoRef.current;
		if (!videoElement) return;

		try {
			if (isPlaying) {
				// If there's a pending play promise, wait for it before pausing
				if (playPromise) {
					try {
						await playPromise;
					} catch (error) {
						// Play was already rejected, safe to pause
						console.log('Play promise was rejected, proceeding with pause');
					}
					setPlayPromise(null);
				}

				videoElement.pause();
				setIsPlaying(false);
			} else {
				// Ensure we're not already trying to play
				if (playPromise) {
					console.log('Play already in progress, waiting...');
					try {
						await playPromise;
						return; // Already playing or will be playing
					} catch (error) {
						// Previous play failed, continue with new play attempt
						setPlayPromise(null);
					}
				}

				// Only show loading if video isn't ready
				if (videoElement.readyState < 3) {
					setIsLoading(true);
				}

				const promise = videoElement.play();
				setPlayPromise(promise);

				if (promise !== undefined) {
					promise
						.then(() => {
							// Playback started successfully
							setIsPlaying(true);
							setIsLoading(false);
							setHasError(false);
							setPlayPromise(null);
						})
						.catch((error) => {
							// Playback failed
							console.error('Video play failed:', error);
							setIsPlaying(false);
							setIsLoading(false);
							setPlayPromise(null);

							// Don't set hasError for user-initiated interruptions
							if (error.name !== 'AbortError') {
								setHasError(true);
							}
						});
				} else {
					// Fallback if play() doesn't return a promise
					setIsLoading(false);
				}
			}
		} catch (error) {
			console.error('Error in togglePlay:', error);
			setIsPlaying(false);
			setIsLoading(false);
			setHasError(true);
			setPlayPromise(null);
		}
	};

	const toggleMute = () => {
		const videoElement = videoRef.current;
		if (!videoElement) return;

		const newMutedState = !isMuted;
		setIsMuted(newMutedState);
		videoElement.muted = newMutedState;
	};

	const handleTimeChange = async (value: number[]) => {
		const videoElement = videoRef.current;
		if (!videoElement) return;

		const newTime = value[0];
		const wasPlaying = isPlaying;

		// If video is playing, pause it first to avoid interruption errors
		if (wasPlaying && playPromise) {
			try {
				await playPromise;
				videoElement.pause();
			} catch (error) {
				// Play was already rejected, safe to seek
			}
		}

		setCurrentTime(newTime);
		videoElement.currentTime = newTime;

		// Resume playing if it was playing before
		if (wasPlaying) {
			setTimeout(() => {
				togglePlay();
			}, 50);
		}
	};

	const handleVolumeChange = (value: number[]) => {
		const videoElement = videoRef.current;
		if (!videoElement) return;

		const newVolume = value[0];
		setVolume(newVolume);
		videoElement.volume = newVolume / 100;

		if (newVolume > 0 && isMuted) {
			setIsMuted(false);
			videoElement.muted = false;
		}
	};

	const skipTime = async (seconds: number) => {
		const videoElement = videoRef.current;
		if (!videoElement) return;

		const newTime = Math.max(0, Math.min(duration, currentTime + seconds));
		const wasPlaying = isPlaying;

		// If video is playing, handle the promise properly
		if (wasPlaying && playPromise) {
			try {
				await playPromise;
			} catch (error) {
				// Play was already rejected
			}
		}

		videoElement.currentTime = newTime;
		setCurrentTime(newTime);

		// If it was playing, continue playing
		if (wasPlaying && !isPlaying) {
			setTimeout(() => {
				togglePlay();
			}, 50);
		}
	};

	const toggleFullscreen = async () => {
		const videoElement = videoRef.current;
		if (!videoElement) return;

		try {
			if (!document.fullscreenElement) {
				await videoElement.requestFullscreen();
				setIsFullscreen(true);
			} else {
				await document.exitFullscreen();
				setIsFullscreen(false);
			}
		} catch (error) {
			console.error('Error toggling fullscreen:', error);
		}
	};

	const handleDownload = () => {
		if (video.downloadUrl) {
			// Create a temporary link element to trigger download
			const link = document.createElement('a');
			link.href = video.downloadUrl;
			link.download = video.title || 'video';
			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
		}
	};

	const handleShare = async () => {
		try {
			if (navigator.share) {
				await navigator.share({
					title: video.title,
					text: video.description,
					url: window.location.href,
				});
			} else {
				// Fallback: copy to clipboard
				await navigator.clipboard.writeText(window.location.href);
			}
		} catch (error) {
			console.error('Error sharing:', error);
		}
	};

	const formatTime = (seconds: number) => {
		if (isNaN(seconds)) return '0:00';

		const hours = Math.floor(seconds / 3600);
		const mins = Math.floor((seconds % 3600) / 60);
		const secs = Math.floor(seconds % 60);

		if (hours > 0) {
			return `${hours}:${mins.toString().padStart(2, '0')}:${secs
				.toString()
				.padStart(2, '0')}`;
		}
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	};

	// Show error state if video fails to load
	if (hasError) {
		return (
			<Card className='overflow-hidden'>
				<CardContent className='p-0'>
					<div className='relative aspect-video bg-black flex items-center justify-center'>
						<div className='text-center text-white'>
							<div className='text-lg font-semibold mb-2'>
								Unable to load video
							</div>
							<div className='text-sm text-gray-300 mb-4'>
								The video file could not be loaded or played
							</div>
							<Button
								variant='outline'
								onClick={() => {
									setHasError(false);
									setIsLoading(true);
									const videoElement = videoRef.current;
									if (videoElement) {
										videoElement.load();
									}
								}}
								className='bg-white/10 border-white/20 text-white hover:bg-white/20'
							>
								Retry
							</Button>
						</div>
						{/* Fallback thumbnail */}
						{video.thumbnail && (
							<img
								src={video.thumbnail}
								alt={video.title}
								className='absolute inset-0 w-full h-full object-cover opacity-30'
							/>
						)}
					</div>
				</CardContent>
			</Card>
		);
	}

	return (
		<Card className='overflow-hidden'>
			<CardContent className='p-0'>
				<div
					className='relative aspect-video bg-black group cursor-pointer'
					onMouseEnter={() => setShowControls(true)}
					onMouseLeave={() => setShowControls(false)}
					onClick={togglePlay}
				>
					{/* Video Element */}
					<video
						ref={videoRef}
						className='w-full h-full object-contain'
						poster={video.thumbnail}
						preload='auto'
						playsInline
						src={video.playUrl}
					>
						Your browser does not support the video tag.
					</video>

					{/* Loading Overlay */}
					{isLoading && (
						<div className='absolute inset-0 bg-black/50 flex items-center justify-center'>
							<div className='w-16 h-16 border-4 border-white/30 border-t-white rounded-full animate-spin'></div>
						</div>
					)}

					{/* Play Overlay (when paused) */}
					{!isPlaying && !isLoading && (
						<div className='absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity duration-200'>
							<Button
								size='lg'
								className='w-20 h-20 rounded-full bg-white/90 hover:bg-white text-black hover:text-black'
								onClick={(e) => {
									e.stopPropagation();
									togglePlay();
								}}
							>
								<Play className='h-8 w-8 ml-1' />
							</Button>
						</div>
					)}

					{/* Video Info Overlay */}
					<div className='absolute top-4 left-4 right-4 flex justify-between items-start'>
						<div className='bg-black/80 text-white px-3 py-1 rounded text-sm max-w-xs'>
							<div className='font-medium truncate'>{video.title}</div>
							<div className='text-xs text-gray-300'>by {video.owner}</div>
						</div>
						<div className='bg-black/80 text-white px-2 py-1 rounded text-xs'>
							{video.dimensions} • {video.codec}
						</div>
					</div>

					{/* Video Controls */}
					<div
						className={`absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent p-4 transition-opacity duration-300 ${
							showControls ? 'opacity-100' : 'opacity-0'
						}`}
						onClick={(e) => e.stopPropagation()}
					>
						{/* Progress Bar */}
						<div className='mb-4'>
							<div className='relative'>
								{/* Buffered progress */}
								<div
									className='absolute h-1 bg-white/30 rounded-full'
									style={{ width: `${buffered}%` }}
								/>
								<Slider
									value={[currentTime]}
									onValueChange={handleTimeChange}
									max={duration}
									step={0.1}
									className='w-full'
								/>
							</div>
							<div className='flex justify-between text-xs text-white/80 mt-1'>
								<span>{formatTime(currentTime)}</span>
								<span>{formatTime(duration)}</span>
							</div>
						</div>

						{/* Control Buttons */}
						<div className='flex items-center justify-between'>
							<div className='flex items-center space-x-2'>
								<Button
									variant='ghost'
									size='sm'
									onClick={togglePlay}
									disabled={isLoading}
									className='text-white hover:text-white hover:bg-white/20'
								>
									{isPlaying ? (
										<Pause className='h-5 w-5' />
									) : (
										<Play className='h-5 w-5' />
									)}
								</Button>

								<Button
									variant='ghost'
									size='sm'
									onClick={() => skipTime(-10)}
									disabled={isLoading}
									className='text-white hover:text-white hover:bg-white/20'
								>
									<SkipBack className='h-4 w-4' />
								</Button>

								<Button
									variant='ghost'
									size='sm'
									onClick={() => skipTime(10)}
									disabled={isLoading}
									className='text-white hover:text-white hover:bg-white/20'
								>
									<SkipForward className='h-4 w-4' />
								</Button>

								<div className='flex items-center space-x-2 ml-4'>
									<Button
										variant='ghost'
										size='sm'
										onClick={toggleMute}
										className='text-white hover:text-white hover:bg-white/20'
									>
										{isMuted || volume === 0 ? (
											<VolumeX className='h-4 w-4' />
										) : (
											<Volume2 className='h-4 w-4' />
										)}
									</Button>
									<div className='w-24'>
										<Slider
											value={[isMuted ? 0 : volume]}
											onValueChange={handleVolumeChange}
											max={100}
											step={1}
											className='w-full'
										/>
									</div>
								</div>
							</div>

							<div className='flex items-center space-x-2'>
								<Button
									variant='ghost'
									size='sm'
									className='text-white hover:text-white hover:bg-white/20'
								>
									<Settings className='h-4 w-4' />
								</Button>
								<Button
									variant='ghost'
									size='sm'
									onClick={toggleFullscreen}
									className='text-white hover:text-white hover:bg-white/20'
								>
									<Maximize className='h-4 w-4' />
								</Button>
							</div>
						</div>
					</div>
				</div>
			</CardContent>
		</Card>
	);
}
