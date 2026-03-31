// app/video/[id]/page.tsx
import { notFound } from 'next/navigation';
import { VideoDetails } from '@/components/video-details';
import { RelatedVideos } from '@/components/related-videos';
import {
	Breadcrumb,
	BreadcrumbItem,
	BreadcrumbLink,
	BreadcrumbList,
	BreadcrumbPage,
	BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import axios from 'axios';
import { formatVideoData } from '@/lib/utils';

interface VideoPageProps {
	params: { id: string };
}

async function getVideoData(videoId: string) {
	try {
		const res = await axios.post(
			'http://localhost:5000/api/videos/query',
			{ video_id: videoId },
			{ headers: { 'x-api-key': 'key1' } }
		);

		// Access videos array inside data
		const videos = res.data?.data?.videos;

		if (!videos || videos.length === 0) {
			console.error('No videos found in response');
			return null;
		}

		const video = videos[0];
		const fvideo = formatVideoData(video);
		return fvideo;
	} catch (error) {
		console.error('Fetch error:', error);
		return null;
	}
}

export default async function VideoPage({ params }: VideoPageProps) {
	const { id: videoId } = await params;
	const video = await getVideoData(videoId);
	console.log('video cat', video?.category);
	if (!video) return notFound();

	return (
		<div className='min-h-screen bg-background'>
			{/* Breadcrumb */}
			<div className='border-b bg-muted/30'>
				<div className='container mx-auto px-4 py-4'>
					<Breadcrumb>
						<BreadcrumbList>
							<BreadcrumbItem>
								<BreadcrumbLink href='/'>Home</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbLink href='/search'>Browse</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbPage>{video.title}</BreadcrumbPage>
							</BreadcrumbItem>
						</BreadcrumbList>
					</Breadcrumb>
				</div>
			</div>

			<div className='container mx-auto px-4 py-8'>
				<div className='flex flex-col lg:flex-row gap-8'>
					{/* Main Content - takes more space on larger screens */}
					<div className='lg:flex-1 space-y-6'>
						<VideoDetails video={video} />
					</div>

					{/* Sidebar - smaller width on larger screens */}
					<div className='lg:w-72 xl:w-80 space-y-6'>
						<RelatedVideos
							key={videoId}
							currentVideoId={videoId}
							category={video.category[0]}
						/>
					</div>
				</div>
			</div>
		</div>
	);
}
