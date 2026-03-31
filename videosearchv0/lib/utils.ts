import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

// Helper function to safely extract values, handling {NULL: true} objects
const safeExtract = (value: any, fallback = '') => {
	if (!value) return fallback;
	if (typeof value === 'object' && value.NULL === true) return fallback;
	return value;
};

// Format duration in seconds to mm:ss
const formatDuration = (seconds: number) => {
	if (!seconds) return '0:00';
	const minutes = Math.floor(seconds / 60);
	const remainingSeconds = Math.floor(seconds % 60);
	return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

// Format file size in bytes to MB
const formatFileSize = (bytes: number) => {
	if (!bytes) return 'Unknown size';
	const mb = bytes / (1024 * 1024);
	return `${mb.toFixed(1)} MB`;
};

// Format upload date from timestamp
const formatUploadDate = (timestamp: number) => {
	if (!timestamp) return new Date().toISOString();
	const dateStr = timestamp.toString();
	if (dateStr.length >= 8) {
		const year = dateStr.substring(0, 4);
		const month = dateStr.substring(4, 6);
		const day = dateStr.substring(6, 8);
		return new Date(`${year}-${month}-${day}`).toISOString();
	}
	return new Date(
		timestamp > 1000000000000 ? timestamp : timestamp * 1000
	).toISOString();
};

// Extract tags from metadata and additional fields
const extractTags = (metadata: any, additional: any) => {
	const tags: string[] = [];

	const height = metadata.height || metadata.Image_Height || 0;
	if (height >= 2160) tags.push('4K');
	else if (height >= 1080) tags.push('HD', '1080p');
	else if (height >= 720) tags.push('HD', '720p');

	if (
		metadata.codec_name === 'hevc' ||
		metadata.Video_Codec?.includes('HEVC')
	) {
		tags.push('HEVC', 'Premium');
	}

	const aiTags = safeExtract(additional?.AI_Tags);
	if (aiTags && typeof aiTags === 'string') {
		tags.push(...aiTags.split(',').map((t: string) => t.trim()));
	}

	if (metadata.Make) tags.push(metadata.Make);
	if (metadata.Model) tags.push(metadata.Model);

	return tags.filter(Boolean);
};

// Calculate aspect ratio from width and height
const calculateAspectRatio = (width: number, height: number) => {
	if (!width || !height) return '16:9';
	const gcd = (a: number, b: number): number => (b === 0 ? a : gcd(b, a % b));
	const divisor = gcd(width, height);
	return `${width / divisor}:${height / divisor}`;
};

// Find service data dynamically
const findServiceData = (apiResponse: any) => {
	if (!apiResponse || typeof apiResponse !== 'object') return null;

	const commonServices = [
		'cts',
		'ftp',
		's3',
		'aws',
		'azure',
		'gcp',
		'cdn',
		'stream',
	];

	for (const service of commonServices) {
		if (apiResponse[service]?.data) return apiResponse[service];
	}

	for (const key in apiResponse) {
		if (apiResponse[key]?.data) return apiResponse[key];
	}

	if (apiResponse.data) return { data: apiResponse.data };

	return null;
};

// Format video data from API response
export const formatVideoData = (apiResponse: any) => {
	const serviceData = findServiceData(apiResponse);
	if (!serviceData) return null;

	const data = serviceData.data;
	const metadata = data.metadata || {};
	const defaultData = data.default || {};
	const additional = data.additional || {};

	return {
		id: apiResponse.video_id || `video-${Date.now()}`,
		title:
			safeExtract(data.title) ||
			safeExtract(defaultData.Name) ||
			'Untitled Video',
		description:
			safeExtract(additional.Description) ||
			safeExtract(data.description) ||
			`Video by ${safeExtract(data.ownerName, 'Unknown User')}`,
		thumbnail:
			data.url?.directUrlPreview ||
			data.url?.preview ||
			'/placeholder.svg?height=200&width=350',
		duration: formatDuration(metadata.duration || defaultData.Time || 0),
		category: data.keyword || [],
		tags: extractTags(metadata, additional),
		uploadDate: formatUploadDate(defaultData.Date_uploaded || data.created),
		views: safeExtract(data.views) || Math.floor(Math.random() * 50000) + 1000,
		license: 'Standard',
		size: formatFileSize(data.size || defaultData.Size),
		codec:
			safeExtract(metadata.Video_Codec) ||
			safeExtract(defaultData.Codec) ||
			'Unknown',
		dimensions: `${data.width || metadata.width || 0}x${
			data.height || metadata.height || 0
		}`,
		owner: safeExtract(data.ownerName, 'Unknown User'),
		approvalStatus: safeExtract(data.approvalStatus || data.status, 'Unknown'),
		playUrl: data.url?.play || data.url?.directUrlPreviewPlay || '',
		directUrlPreviewPlay: data.url?.directUrlPreviewPlay || '',
		downloadUrl: data.url?.download || '',
		detailUrl: data.url?.detail || '',
		bitRate: metadata.bit_rate
			? `${(metadata.bit_rate / 1000000).toFixed(2)} Mbps`
			: 'Unknown',
		frameRate: metadata.Video_Frame_Rate
			? `${metadata.Video_Frame_Rate.toFixed(0)}fps`
			: '30fps',
		aspectRatio: calculateAspectRatio(
			data.width || metadata.width,
			data.height || metadata.height
		),
		audioCodec: metadata.Audio_Format || 'AAC',
		sampleRate: metadata.Audio_Sample_Rate
			? `${metadata.Audio_Sample_Rate}Hz`
			: '44.1kHz',
		colorProfile: metadata.color_primaries || 'bt709',
		credit: safeExtract(additional.Credit, ''),
		location: safeExtract(additional.Location, ''),
		textVector: apiResponse.text_vector || [],
		originalData: apiResponse,
	};
};

// Alternative: allow specifying service name directly
export const formatVideoDataWithService = (
	apiResponse: any,
	serviceName?: string
) => {
	const serviceData =
		serviceName && apiResponse[serviceName]?.data
			? apiResponse[serviceName]
			: findServiceData(apiResponse);
	if (!serviceData) return null;
	return formatVideoData({ ...apiResponse, ...serviceData });
};

// Generate timestamp like "yyyyMMddHHmmssSSS"
export function getFormattedTimestamp() {
	const now = new Date();
	const yyyy = now.getFullYear();
	const MM = String(now.getMonth() + 1).padStart(2, '0');
	const dd = String(now.getDate()).padStart(2, '0');
	const HH = String(now.getHours()).padStart(2, '0');
	const mm = String(now.getMinutes()).padStart(2, '0');
	const ss = String(now.getSeconds()).padStart(2, '0');
	const SSS = String(now.getMilliseconds()).padStart(3, '0');
	return `${yyyy}${MM}${dd}${HH}${mm}${ss}${SSS}`;
}

console.log(getFormattedTimestamp());
