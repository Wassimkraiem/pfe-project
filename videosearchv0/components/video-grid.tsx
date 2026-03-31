import { VideoCard } from '@/components/video-card';

interface Video {
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
	directUrlPreviewPlay: string;
}

interface VideoGridProps {
	videos: Video[];
	className?: string;
}

export function VideoGrid({ videos, className = '' }: VideoGridProps) {
	return (
		<div
			className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 ${className}`}
		>
			{videos.map((video) => (
				<VideoCard key={video.id} video={video} />
			))}
		</div>
	);
}
