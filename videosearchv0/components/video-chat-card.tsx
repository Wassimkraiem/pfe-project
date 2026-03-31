import { Film } from 'lucide-react';

export type VideoResult = {
	video_id: string;
	title?: string;
	description?: string;
	tags?: string[];
	keywords?: string[];
	duration?: string | number;
	resolution?: string;
	orientation?: string;
	owner?: string;
	thumbnail?: string;
	playUrl?: string;
	directUrlPreviewPlay?: string;
	directUrlOriginal?: string;
};

export function VideoChatCard({
	video,
	onClick,
}: {
	video: VideoResult;
	onClick?: () => void;
}) {
	return (
		<button
			type='button'
			onClick={onClick}
			className='flex w-full gap-1.5 rounded-md border bg-card p-1.5 text-[11px] leading-tight text-left transition-colors hover:bg-muted/50'
		>
			<div className='flex h-8 w-8 flex-shrink-0 items-center justify-center rounded bg-muted overflow-hidden'>
				{video.thumbnail ? (
					// eslint-disable-next-line @next/next/no-img-element
					<img
						src={video.thumbnail}
						alt={video.title ?? video.video_id}
						className='h-8 w-8 rounded object-cover'
					/>
				) : (
					<Film className='h-3.5 w-3.5 text-muted-foreground' />
				)}
			</div>
			<div className='min-w-0 flex-1'>
				<p className='font-semibold truncate leading-tight'>{video.title || video.video_id}</p>
				{video.description && (
					<p className='text-muted-foreground truncate text-[10px]'>{video.description}</p>
				)}
				<div className='flex gap-0.5 mt-0.5 flex-wrap'>
					{video.duration && (
						<span className='rounded bg-muted px-1 py-px text-[9px] font-medium'>
							{video.duration}s
						</span>
					)}
					{video.owner && (
						<span className='rounded bg-muted px-1 py-px text-[9px]'>
							{video.owner}
						</span>
					)}
				</div>
			</div>
		</button>
	);
}
