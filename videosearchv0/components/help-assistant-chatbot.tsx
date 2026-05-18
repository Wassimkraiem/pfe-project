'use client';

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
	addConversationMessages,
	ConversationSummary,
	createConversation,
	deleteConversation,
	getConversation,
	getConversations,
} from '@/lib/conversations-api';
import {
	createPlaylist,
	addVideosToPlaylist,
	getPlaylists,
	type PlaylistSummary,
} from '@/lib/playlists-api';
import { VideoChatCard, type VideoResult } from '@/components/video-chat-card';

type ChatRole = 'user' | 'assistant';

interface ChatMessage {
	id: string;
	role: ChatRole;
	content: string;
	videos?: VideoResult[];
}

const CHAT_API_URL = '/api/chat';
const TRANSCRIBE_API_URL = '/api/transcribe';
const WELCOME_MESSAGE: ChatMessage = {
	id: 'welcome',
	role: 'assistant',
	content:
		'Hi, I am your BVIRAL assistant. Ask me anything about finding videos, licensing, or account usage. I can search the video library for you!',
};

function extractAssistantReply(payload: any): string {
	if (!payload) return 'I could not read a response from the assistant.';
	if (typeof payload === 'string') return payload;

	return (
		payload.reply ||
		payload.response ||
		payload.answer ||
		payload.message ||
		payload.data?.reply ||
		payload.data?.response ||
		payload.data?.answer ||
		payload.data?.message ||
		'I could not read a response from the assistant.'
	);
}

function extractVideos(payload: any): VideoResult[] {
	if (!payload) return [];
	const videos = payload.videos ?? payload.data?.videos;
	if (Array.isArray(videos)) return videos;
	return [];
}

function extractVideosFromMessagePayload(payload: unknown): VideoResult[] {
	if (!payload || typeof payload !== 'object') return [];
	const maybeVideos = (payload as { videos?: unknown }).videos;
	if (!Array.isArray(maybeVideos)) return [];
	return maybeVideos.filter(
		(item): item is VideoResult =>
			!!item && typeof item === 'object' && typeof (item as VideoResult).video_id === 'string'
	);
}

function getPlayableUrl(video: VideoResult): string {
	return (
		video.directUrlPreviewPlay ||
		video.playUrl ||
		video.directUrlOriginal ||
		''
	);
}

function formatDuration(duration?: string | number): string | null {
	if (duration === undefined || duration === null || duration === '') return null;
	const value = Number(duration);
	if (!Number.isFinite(value)) return String(duration);
	const total = Math.max(0, Math.round(value));
	const mins = Math.floor(total / 60);
	const secs = total % 60;
	return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function parseNumberLike(value: unknown): number | undefined {
	if (typeof value === 'number' && Number.isFinite(value)) return value;
	if (typeof value === 'string') {
		const cleaned = value.trim().replace(/,/g, '');
		if (!cleaned) return undefined;
		const parsed = Number(cleaned);
		if (Number.isFinite(parsed)) return parsed;
	}
	return undefined;
}

function deriveVideoDetailsFromDoc(doc: any): Partial<VideoResult> {
	if (!doc || typeof doc !== 'object') return {};

	const rmsData = doc?.rms?.data && typeof doc.rms.data === 'object' ? doc.rms.data : {};
	const ctsData = doc?.cts?.data && typeof doc.cts.data === 'object' ? doc.cts.data : {};

	// Some records have partial fields in rms and richer fields in cts (or vice versa).
	// Read values across both sources to avoid dropping metadata like views.
	const sources = [rmsData, ctsData].filter(
		(item) => item && typeof item === 'object' && Object.keys(item).length > 0
	);
	const pickFirst = <T,>(selector: (item: any) => T | undefined): T | undefined => {
		for (const source of sources) {
			const value = selector(source);
			if (value !== undefined && value !== null && value !== '') return value;
		}
		return undefined;
	};
	const metadata =
		pickFirst((item) =>
			item?.metadata && typeof item.metadata === 'object' ? item.metadata : undefined
		) || {};
	const url =
		pickFirst((item) => (item?.url && typeof item.url === 'object' ? item.url : undefined)) || {};
	const views =
		parseNumberLike(pickFirst((item) => item?.views)) ??
		parseNumberLike((metadata as any)?.views) ??
		parseNumberLike((metadata as any)?.view_count);

	return {
		video_id: doc.video_id || pickFirst((item) => item?.id) || '',
		title: pickFirst((item) => item?.name || item?.additional?.Title) || '',
		description: pickFirst((item) => item?.description || item?.additional?.Description) || '',
		views,
		duration:
			pickFirst((item) => item?.metadata?.RDuration) ??
			pickFirst((item) => item?.metadata?.duration) ??
			pickFirst((item) => item?.cts?.duration),
		resolution: pickFirst((item) => item?.default?.Dimensions) || '',
		orientation: metadata.Orientation || '',
		owner: pickFirst((item) => item?.ownerName) || '',
		tags: (pickFirst((item) => (Array.isArray(item?.tag) ? item.tag : undefined)) || []) as string[],
		keywords: (pickFirst((item) => (Array.isArray(item?.keyword) ? item.keyword : undefined)) || []) as string[],
		directUrlPreviewPlay: typeof url.directUrlPreviewPlay === 'string' ? url.directUrlPreviewPlay : undefined,
		directUrlOriginal: typeof url.directUrlOriginal === 'string' ? url.directUrlOriginal : undefined,
		playUrl: typeof url.play === 'string' ? url.play : undefined,
	};
}

export function HelpAssistantChatbot() {
	const { isLoaded, isSignedIn, getToken } = useAuth();
	const [isOpen, setIsOpen] = useState(false);
	const [isSending, setIsSending] = useState(false);
	const [input, setInput] = useState('');
	const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);

	const [conversations, setConversations] = useState<ConversationSummary[]>([]);
	const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
	const [isLoadingHistory, setIsLoadingHistory] = useState(false);
	const [showHistory, setShowHistory] = useState(false);

	const [savingPlaylist, setSavingPlaylist] = useState(false);
	const [viewerVideos, setViewerVideos] = useState<VideoResult[] | null>(null);
	const [viewerIndex, setViewerIndex] = useState(0);
	const [viewerUrl, setViewerUrl] = useState('');
	const [viewerLoading, setViewerLoading] = useState(false);
	const [viewerError, setViewerError] = useState<string | null>(null);
	const [viewerDetails, setViewerDetails] = useState<VideoResult | null>(null);
	const [isRecording, setIsRecording] = useState(false);
	const [isTranscribing, setIsTranscribing] = useState(false);
	const [recordingError, setRecordingError] = useState<string | null>(null);

	const bottomRef = useRef<HTMLDivElement | null>(null);
	const historyLoadedRef = useRef(false);
	const recorderRef = useRef<MediaRecorder | null>(null);
	const streamRef = useRef<MediaStream | null>(null);
	const chunksRef = useRef<BlobPart[]>([]);
	const currentViewerVideo = viewerVideos ? viewerVideos[viewerIndex] : null;
	const activeViewerVideo = viewerDetails || currentViewerVideo;

	const openViewer = (videos: VideoResult[], index: number) => {
		if (!videos.length) return;
		setViewerVideos(videos);
		setViewerIndex(index);
		setViewerUrl('');
		setViewerError(null);
		setViewerDetails(videos[index] || null);
	};

	const closeViewer = () => {
		setViewerVideos(null);
		setViewerIndex(0);
		setViewerUrl('');
		setViewerError(null);
		setViewerDetails(null);
	};

	const goPrevViewer = () => {
		setViewerIndex((idx) => (idx > 0 ? idx - 1 : idx));
	};

	const goNextViewer = () => {
		if (!viewerVideos) return;
		setViewerIndex((idx) => (idx < viewerVideos.length - 1 ? idx + 1 : idx));
	};

	useEffect(() => {
		if (!currentViewerVideo) return;
		setViewerDetails(currentViewerVideo);

		const direct = getPlayableUrl(currentViewerVideo);
		let hasDirectUrl = false;
		if (direct) {
			hasDirectUrl = true;
			setViewerUrl(direct);
			setViewerError(null);
		} else {
			setViewerUrl('');
		}

		let cancelled = false;
		const loadFromApi = async () => {
			setViewerLoading(true);
			setViewerError(null);
			try {
				const response = await fetch(
					'/api/videos/query',
					{
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
						},
						body: JSON.stringify({ video_id: currentViewerVideo.video_id }),
					}
				);

				if (!response.ok) {
					throw new Error(`Video API returned ${response.status}`);
				}

				const payload = await response.json();
				const doc = payload?.data?.videos?.[0];
				const derived = deriveVideoDetailsFromDoc(doc);
				const url = doc?.rms?.data?.url || doc?.cts?.data?.url;
				const resolved =
					derived.directUrlPreviewPlay ||
					derived.playUrl ||
					derived.directUrlOriginal ||
					url?.directUrlPreviewPlay ||
					url?.play ||
					url?.directUrlOriginal ||
					url?.preview ||
					'';

				if (!cancelled) {
					setViewerDetails((prev) => ({
						...(prev || currentViewerVideo),
						...derived,
					}));
					if (resolved) {
						setViewerUrl(resolved);
						setViewerError(null);
					} else if (!hasDirectUrl) {
						setViewerError('No playable URL found for this video.');
					}
				}
			} catch {
				if (!cancelled) {
					if (!hasDirectUrl) setViewerError('Could not load this video right now.');
				}
			} finally {
				if (!cancelled) setViewerLoading(false);
			}
		};

		loadFromApi();
		return () => {
			cancelled = true;
		};
	}, [currentViewerVideo]);

	const scrollToBottom = useCallback(() => {
		requestAnimationFrame(() => {
			bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
		});
	}, []);

	useEffect(() => {
		if (isOpen) scrollToBottom();
	}, [isOpen, messages, isSending, scrollToBottom]);

	const fetchToken = useCallback(async (): Promise<string | null> => {
		if (!isSignedIn) return null;
		return getToken();
	}, [isSignedIn, getToken]);

	const loadConversations = useCallback(async () => {
		const token = await fetchToken();
		if (!token) return;
		try {
			const list = await getConversations(token);
			setConversations(list);
			return list;
		} catch {
			/* silent */
		}
	}, [fetchToken]);

	const loadConversation = useCallback(
		async (id: number) => {
			const token = await fetchToken();
			if (!token) return;
			setIsLoadingHistory(true);
			try {
				const detail = await getConversation(token, id);
				const loaded: ChatMessage[] = detail.messages.map((m) => ({
					id: `db-${m.id}`,
					role: m.role,
					content: m.content,
					videos:
						m.role === 'assistant'
							? extractVideosFromMessagePayload(m.payload)
							: undefined,
				}));
				setMessages(loaded.length > 0 ? loaded : [WELCOME_MESSAGE]);
				setActiveConversationId(id);
				setShowHistory(false);
			} catch {
				/* silent */
			} finally {
				setIsLoadingHistory(false);
			}
		},
		[fetchToken],
	);

	useEffect(() => {
		if (!isOpen || !isSignedIn || historyLoadedRef.current) return;
		historyLoadedRef.current = true;
		(async () => {
			const list = await loadConversations();
			if (list && list.length > 0) {
				await loadConversation(list[0].id);
			}
		})();
	}, [isOpen, isSignedIn, loadConversations, loadConversation]);

	const startNewChat = () => {
		setActiveConversationId(null);
		setMessages([WELCOME_MESSAGE]);
		setShowHistory(false);
	};

	const handleDeleteConversation = async (id: number) => {
		const token = await fetchToken();
		if (!token) return;
		try {
			await deleteConversation(token, id);
			setConversations((prev) => prev.filter((c) => c.id !== id));
			if (activeConversationId === id) startNewChat();
		} catch {
			/* silent */
		}
	};

	const handleSaveAsPlaylist = async (videos: VideoResult[]) => {
		if (!isSignedIn || videos.length === 0) return;
		const token = await fetchToken();
		if (!token) return;

		setSavingPlaylist(true);
		try {
			const videoIds = videos.map((v) => v.video_id).filter(Boolean);
			const title = `Search results – ${new Date().toLocaleDateString()}`;
			await createPlaylist(token, { title, video_ids: videoIds });

			setMessages((cur) => [
				...cur,
				{
					id: `sys-${Date.now()}`,
					role: 'assistant',
					content: `Playlist "${title}" saved with ${videoIds.length} video(s). View it in your dashboard under My Playlists.`,
				},
			]);
		} catch {
			setMessages((cur) => [
				...cur,
				{
					id: `sys-err-${Date.now()}`,
					role: 'assistant',
					content: 'Failed to save playlist. Please try again.',
				},
			]);
		} finally {
			setSavingPlaylist(false);
		}
	};

	const handleSubmit = async (event: FormEvent) => {
		event.preventDefault();
		const text = input.trim();
		if (!text || isSending || isTranscribing) return;

		const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: 'user', content: text };
		const nextMessages = [...messages, userMsg];
		setMessages(nextMessages);
		setInput('');
		setIsSending(true);
		scrollToBottom();

		try {
			const response = await fetch(CHAT_API_URL, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					input_message: text,
					message: text,
					mode: 'auto',
					history: nextMessages.map((m) => ({ role: m.role, content: m.content })),
				}),
			});

			if (!response.ok) throw new Error(`Chat API returned ${response.status}`);

			const payload = await response.json();
			const extractedAssistantText = extractAssistantReply(payload);
			const videos = extractVideos(payload);
			const assistantText =
				extractedAssistantText === 'I could not read a response from the assistant.' &&
				videos.length > 0
					? `Found ${videos.length} video${videos.length === 1 ? '' : 's'} for your request.`
					: extractedAssistantText;
			const assistantPayload =
				videos.length > 0
					? ({
							videos,
							reply: assistantText,
						} as const)
					: undefined;

			const assistantMsg: ChatMessage = {
				id: `a-${Date.now()}`,
				role: 'assistant',
				content: assistantText,
				videos: videos.length > 0 ? videos : undefined,
			};
			setMessages((cur) => [...cur, assistantMsg]);

			if (isSignedIn) {
				const token = await fetchToken();
				if (token) {
					try {
						if (activeConversationId) {
							await addConversationMessages(token, activeConversationId, {
								user_message: text,
								assistant_message: assistantText,
								assistant_payload: assistantPayload,
							});
						} else {
							const created = await createConversation(token, {
								user_message: text,
								assistant_message: assistantText,
								assistant_payload: assistantPayload,
							});
							setActiveConversationId(created.id);
							setConversations((prev) => [created, ...prev]);
						}
					} catch {
						/* persistence failure is non-blocking */
					}
				}
			}
		} catch {
			setMessages((cur) => [
				...cur,
				{
					id: `a-error-${Date.now()}`,
					role: 'assistant',
					content:
						'Sorry, I could not reach the assistant service right now. Please try again.',
				},
			]);
		} finally {
			setIsSending(false);
			scrollToBottom();
		}
	};

	const stopRecording = useCallback(() => {
		const recorder = recorderRef.current;
		if (recorder && recorder.state !== 'inactive') {
			recorder.stop();
		}
	}, []);

	const startRecording = useCallback(async () => {
		setRecordingError(null);
		if (!navigator.mediaDevices?.getUserMedia) {
			setRecordingError('Voice input is not supported in this browser.');
			return;
		}

		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			streamRef.current = stream;
			chunksRef.current = [];

			const mimeType =
				typeof MediaRecorder !== 'undefined' &&
				MediaRecorder.isTypeSupported('audio/webm')
					? 'audio/webm'
					: '';
			const recorder = mimeType
				? new MediaRecorder(stream, { mimeType })
				: new MediaRecorder(stream);
			recorderRef.current = recorder;

			recorder.ondataavailable = (event) => {
				if (event.data && event.data.size > 0) {
					chunksRef.current.push(event.data);
				}
			};

			recorder.onstop = async () => {
				setIsRecording(false);
				const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
				chunksRef.current = [];
				streamRef.current?.getTracks().forEach((track) => track.stop());
				streamRef.current = null;

				if (!audioBlob.size) return;

				setIsTranscribing(true);
				try {
					const formData = new FormData();
					formData.append('audio', audioBlob, 'recording.webm');
					const response = await fetch(TRANSCRIBE_API_URL, {
						method: 'POST',
						body: formData,
					});
					if (!response.ok) throw new Error(`Transcription failed (${response.status})`);
					const payload = (await response.json()) as { text?: string };
					const transcript = (payload.text ?? '').trim();
					if (transcript) {
						setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
					}
				} catch {
					setRecordingError('Could not transcribe audio. Please try again.');
				} finally {
					setIsTranscribing(false);
				}
			};

			recorder.start();
			setIsRecording(true);
		} catch {
			setRecordingError('Microphone access was denied.');
			streamRef.current?.getTracks().forEach((track) => track.stop());
			streamRef.current = null;
		}
	}, []);

	useEffect(() => {
		return () => {
			if (recorderRef.current && recorderRef.current.state !== 'inactive') {
				recorderRef.current.stop();
			}
			streamRef.current?.getTracks().forEach((track) => track.stop());
		};
	}, []);

	if (!isLoaded || !isSignedIn) return null;

	return (
		<div className='fixed bottom-3 right-3 z-50'>
			{isOpen ? (
				<div className='w-[88vw] max-w-sm rounded-xl border bg-background shadow-xl text-[13px]'>
					{/* Header */}
					<div className='flex items-center justify-between border-b px-3 py-2'>
						<div className='flex items-center gap-1.5'>
							{showHistory && (
								<Button type='button' variant='ghost' size='sm' className='h-6 w-6 p-0 text-xs' onClick={() => setShowHistory(false)}>
									&larr;
								</Button>
							)}
							<div>
								<p className='text-[13px] font-semibold leading-tight'>
									{showHistory ? 'History' : 'Video Search'}
								</p>
								{!showHistory && (
									<p className='text-[10px] text-muted-foreground leading-tight'>
										AI routing enabled
									</p>
								)}
							</div>
						</div>
						<div className='flex items-center gap-0.5'>
							{!showHistory && (
								<>
									<Button type='button' variant='ghost' size='sm' className='h-6 w-6 p-0 text-[10px]' title='History' onClick={() => { loadConversations(); setShowHistory(true); }}>
										&#x1f4cb;
									</Button>
									<Button type='button' variant='ghost' size='sm' className='h-6 w-6 p-0 text-xs' title='New chat' onClick={startNewChat}>
										+
									</Button>
								</>
							)}
							<Button type='button' variant='ghost' size='sm' className='h-6 text-[11px] px-1.5' onClick={() => setIsOpen(false)}>
								✕
							</Button>
						</div>
					</div>

					{/* Body */}
					{showHistory ? (
						<div className='h-80 overflow-y-auto'>
							{conversations.length === 0 ? (
								<p className='text-xs text-muted-foreground text-center mt-8'>No past conversations</p>
							) : (
								conversations.map((conv) => (
									<div
										key={conv.id}
										className={`flex items-center justify-between px-3 py-2 border-b cursor-pointer hover:bg-muted/50 ${conv.id === activeConversationId ? 'bg-muted' : ''}`}
										onClick={() => loadConversation(conv.id)}
									>
										<div className='flex-1 overflow-hidden mr-1.5'>
											<p className='text-[12px] font-medium truncate'>{conv.title || 'Untitled'}</p>
											<p className='text-[10px] text-muted-foreground'>{new Date(conv.created_at).toLocaleDateString()}</p>
										</div>
										<Button type='button' variant='ghost' size='sm' className='h-6 w-6 p-0 text-muted-foreground hover:text-destructive text-xs' title='Delete' onClick={(e) => { e.stopPropagation(); handleDeleteConversation(conv.id); }}>
											&times;
										</Button>
									</div>
								))
							)}
						</div>
					) : (
						<>
							<div className='h-80 overflow-y-auto px-2.5 py-2 space-y-2'>
								{isLoadingHistory ? (
									<div className='flex items-center justify-center h-full'>
										<p className='text-xs text-muted-foreground'>Loading...</p>
									</div>
								) : (
									messages.map((message) => (
										<div key={message.id}>
											<div className={`max-w-[88%] rounded-lg px-2.5 py-1.5 text-[12px] leading-relaxed ${message.role === 'user' ? 'ml-auto bg-primary text-primary-foreground' : 'bg-muted text-foreground'}`}>
												{message.content}
											</div>
											{message.videos && message.videos.length > 0 && (
												<div className='mt-1.5 space-y-1 max-w-[92%]'>
													{message.videos.map((v, idx) => (
														<VideoChatCard
															key={v.video_id}
															video={v}
															onClick={() => openViewer(message.videos!, idx)}
														/>
													))}
													<Button type='button' variant='outline' size='sm' className='mt-0.5 text-[11px] w-full h-7' disabled={savingPlaylist} onClick={() => handleSaveAsPlaylist(message.videos!)}>
														{savingPlaylist ? 'Saving…' : '💾 Save as Playlist'}
													</Button>
												</div>
											)}
										</div>
									))
								)}
								{isSending && (
									<div className='max-w-[88%] rounded-lg px-2.5 py-1.5 text-[12px] bg-muted text-foreground animate-pulse'>
										Thinking…
									</div>
								)}
								<div ref={bottomRef} />
							</div>

							<form onSubmit={handleSubmit} className='border-t px-2.5 py-2 flex gap-1.5'>
								<Input
									value={input}
									onChange={(event) => setInput(event.target.value)}
									placeholder={isRecording ? 'Listening...' : 'Ask a question…'}
									disabled={isSending || isTranscribing}
									className='h-8 text-[12px]'
								/>
								<Button
									type='button'
									variant='outline'
									onClick={isRecording ? stopRecording : startRecording}
									disabled={isSending || isTranscribing}
									className='h-8 px-2 text-[12px]'
									title={isRecording ? 'Stop recording' : 'Start voice input'}
								>
									{isRecording ? '■' : '🎤'}
								</Button>
								<Button
									type='submit'
									disabled={isSending || isTranscribing || !input.trim()}
									className='h-8 px-3 text-[12px]'
								>
									Send
								</Button>
							</form>
							{(isRecording || isTranscribing || recordingError) && (
								<div className='px-2.5 pb-2'>
									<p className={`text-[11px] ${recordingError ? 'text-destructive' : 'text-muted-foreground'}`}>
										{recordingError
											? recordingError
											: isTranscribing
												? 'Transcribing audio...'
												: 'Recording... click stop when done.'}
									</p>
								</div>
							)}
						</>
					)}
				</div>
			) : (
				<Button type='button' className='rounded-full px-4 h-9 text-[12px] shadow-lg' onClick={() => setIsOpen(true)}>
					Video Search
				</Button>
			)}
			{viewerVideos && (
				<div className='fixed inset-0 z-[70] bg-black/70 p-4 flex items-center justify-center'>
					<div className='w-full max-w-3xl rounded-lg bg-background border shadow-2xl'>
						<div className='flex items-center justify-between border-b px-3 py-2'>
							<div className='min-w-0'>
								<p className='text-sm font-semibold truncate'>
									{activeViewerVideo?.title || activeViewerVideo?.video_id}
								</p>
								<p className='text-xs text-muted-foreground'>
									Video {viewerIndex + 1} of {viewerVideos.length}
								</p>
							</div>
							<Button type='button' variant='ghost' size='sm' onClick={closeViewer}>
								Close
							</Button>
						</div>
						<div className='p-3'>
							<div className='aspect-video w-full rounded-md bg-black overflow-hidden'>
								{viewerLoading ? (
									<div className='h-full w-full flex items-center justify-center text-xs text-white/80'>
										Loading video...
									</div>
								) : viewerError ? (
									<div className='h-full w-full flex items-center justify-center text-xs text-white/80'>
										{viewerError}
									</div>
								) : viewerUrl ? (
									<video
										key={`${activeViewerVideo?.video_id}-${viewerUrl}`}
										src={viewerUrl}
										controls
										autoPlay
										className='h-full w-full'
									/>
								) : (
									<div className='h-full w-full flex items-center justify-center text-xs text-white/80'>
										No video URL available.
									</div>
								)}
							</div>
							<div className='mt-3 rounded-md border p-2.5 text-xs space-y-2'>
								<div className='grid grid-cols-2 gap-2'>
									<div>
										<p className='text-muted-foreground'>Views</p>
										<p className='font-medium'>
											{typeof activeViewerVideo?.views === 'number'
												? activeViewerVideo.views.toLocaleString()
												: 'N/A'}
										</p>
									</div>
									<div>
										<p className='text-muted-foreground'>Duration</p>
										<p className='font-medium'>
											{formatDuration(activeViewerVideo?.duration) || 'N/A'}
										</p>
									</div>
									<div>
										<p className='text-muted-foreground'>Resolution</p>
										<p className='font-medium'>{activeViewerVideo?.resolution || 'N/A'}</p>
									</div>
									<div>
										<p className='text-muted-foreground'>Orientation</p>
										<p className='font-medium'>{activeViewerVideo?.orientation || 'N/A'}</p>
									</div>
								</div>
								<div>
									<p className='text-muted-foreground'>Owner</p>
									<p className='font-medium'>{activeViewerVideo?.owner || 'N/A'}</p>
								</div>
								<div>
									<p className='text-muted-foreground'>Video ID</p>
									<p className='font-mono break-all'>{activeViewerVideo?.video_id || 'N/A'}</p>
								</div>
								{activeViewerVideo?.description && (
									<div>
										<p className='text-muted-foreground'>Description</p>
										<p className='leading-relaxed'>{activeViewerVideo.description}</p>
									</div>
								)}
								{((activeViewerVideo?.keywords && activeViewerVideo.keywords.length > 0) ||
									(activeViewerVideo?.tags && activeViewerVideo.tags.length > 0)) && (
									<div>
										<p className='text-muted-foreground mb-1'>Keywords / Tags</p>
										<div className='flex flex-wrap gap-1'>
											{[...(activeViewerVideo?.keywords || []), ...(activeViewerVideo?.tags || [])]
												.filter(Boolean)
												.slice(0, 20)
												.map((item, idx) => (
													<span
														key={`${item}-${idx}`}
														className='rounded bg-muted px-1.5 py-0.5 text-[11px]'
													>
														{item}
													</span>
												))}
										</div>
									</div>
								)}
							</div>
							<div className='mt-3 flex items-center justify-between gap-2'>
								<Button
									type='button'
									variant='outline'
									size='sm'
									onClick={goPrevViewer}
									disabled={viewerIndex === 0}
								>
									Previous
								</Button>
								<Button
									type='button'
									variant='outline'
									size='sm'
									onClick={goNextViewer}
									disabled={viewerIndex >= viewerVideos.length - 1}
								>
									Next
								</Button>
							</div>
						</div>
					</div>
				</div>
			)}
		</div>
	);
}
