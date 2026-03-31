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

export function HelpAssistantChatbot() {
	const { isLoaded, isSignedIn, getToken } = useAuth();
	const [isOpen, setIsOpen] = useState(false);
	const [isSending, setIsSending] = useState(false);
	const [input, setInput] = useState('');
	const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
	const [chatMode, setChatMode] = useState<'default' | 'video_search'>('video_search');

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

	const bottomRef = useRef<HTMLDivElement | null>(null);
	const historyLoadedRef = useRef(false);
	const currentViewerVideo = viewerVideos ? viewerVideos[viewerIndex] : null;

	const openViewer = (videos: VideoResult[], index: number) => {
		if (!videos.length) return;
		setViewerVideos(videos);
		setViewerIndex(index);
		setViewerUrl('');
		setViewerError(null);
	};

	const closeViewer = () => {
		setViewerVideos(null);
		setViewerIndex(0);
		setViewerUrl('');
		setViewerError(null);
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

		const direct = getPlayableUrl(currentViewerVideo);
		if (direct) {
			setViewerUrl(direct);
			setViewerError(null);
			return;
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
				const url = payload?.data?.videos?.[0]?.rms?.data?.url;
				const resolved =
					url?.directUrlPreviewPlay ||
					url?.play ||
					url?.directUrlOriginal ||
					url?.preview ||
					'';

				if (!cancelled) {
					if (resolved) {
						setViewerUrl(resolved);
						setViewerError(null);
					} else {
						setViewerError('No playable URL found for this video.');
					}
				}
			} catch {
				if (!cancelled) {
					setViewerError('Could not load this video right now.');
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
		if (!text || isSending) return;

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
					mode: chatMode,
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
										{chatMode === 'video_search' ? 'Describe what you need' : 'BVIRAL assistant'}
									</p>
								)}
							</div>
						</div>
						<div className='flex items-center gap-0.5'>
							{!showHistory && (
								<>
									<Button type='button' variant={chatMode === 'video_search' ? 'default' : 'ghost'} size='sm' className='h-6 text-[10px] px-1.5' title='Toggle mode' onClick={() => setChatMode((m) => m === 'video_search' ? 'default' : 'video_search')}>
										{chatMode === 'video_search' ? '🎬' : '💬'}
									</Button>
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
										{chatMode === 'video_search' ? 'Searching videos…' : 'Thinking…'}
									</div>
								)}
								<div ref={bottomRef} />
							</div>

							<form onSubmit={handleSubmit} className='border-t px-2.5 py-2 flex gap-1.5'>
								<Input
									value={input}
									onChange={(event) => setInput(event.target.value)}
									placeholder={chatMode === 'video_search' ? 'Describe the videos you need…' : 'Ask a question…'}
									disabled={isSending}
									className='h-8 text-[12px]'
								/>
								<Button type='submit' disabled={isSending || !input.trim()} className='h-8 px-3 text-[12px]'>
									Send
								</Button>
							</form>
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
									{currentViewerVideo?.title || currentViewerVideo?.video_id}
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
										key={`${currentViewerVideo?.video_id}-${viewerUrl}`}
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
