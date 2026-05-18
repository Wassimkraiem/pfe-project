'use client';

import { memo, useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { VideoCard } from '@/components/video-card';
import { Button } from '@/components/ui/button';
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '@/components/ui/select';
import {
	ChevronLeft,
	ChevronRight,
	Grid3X3,
	List,
	ChevronDown,
	ChevronUp,
	Filter,
	Calendar,
} from 'lucide-react';
import axios from 'axios';
import { formatVideoData } from './../lib/utils';
import { useCategories } from '@/app/context/CategoriesContext';
import { useAuth } from '@clerk/nextjs';
import {
	ingestRecommendationClickEvent,
	ingestRecommendationSearchEvent,
} from '@/lib/recommendations-api';

interface SearchResultsProps {
	query: string;
	category: string;
	count: string;
}

interface FacetData {
	locations: string[];
	durations: number[];
	created_dates: Array<{
		key: number;
		doc_count: number;
	}>;
	resolutions: string[];
	orientation: string[];
	tags: Array<{
		key: string;
		doc_count: number;
	}>;
}

const RESULTS_PER_PAGE = 30;

export const SearchResults = memo(function SearchResults({
	query,
	category,
	count,
}: SearchResultsProps) {
	const { categories } = useCategories();
	const { isLoaded, isSignedIn, getToken } = useAuth();
	const router = useRouter();
	const pathname = usePathname();
	const searchParams = useSearchParams();
	const searchEventKeyRef = useRef('');
	const fetchAbortRef = useRef<AbortController | null>(null);

	const [currentPage, setCurrentPage] = useState(1);
	const [sortBy, setSortBy] = useState('relevance');
	const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
	const [videos, setVideos] = useState<any[]>([]);
	const [totalResults, setTotalResults] = useState(0);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState('');
	const [execution, setExecution] = useState<Record<string, number> | null>(
		null
	);

	// Facets data from API
	const [facetsData, setFacetsData] = useState<FacetData>({
		locations: [],
		durations: [],
		created_dates: [],
		resolutions: [],
		orientation: [],
		tags: [],
	});

	// Sidebar collapse state
	const [sidebarOpen, setSidebarOpen] = useState(true);
	const [expandedSections, setExpandedSections] = useState({
		categories: false,
		tags: false,
		duration: false,
		dateRange: false,
		location: false,
		resolution: false,
		orientation: false,
	});

	// Filter state - Initialize from URL params
	const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
	const [selectedTags, setSelectedTags] = useState<string[]>([]);
	const [durationRange, setDurationRange] = useState<[number, number]>([
		0, 300,
	]);
	const [selectedDateRange, setSelectedDateRange] = useState<{
		start: string;
		end: string;
	}>({
		start: '',
		end: '',
	});
	const [selectedLocation, setSelectedLocation] = useState<string[]>([]);
	const [selectedResolution, setSelectedResolution] = useState<string[]>([]);
	const [selectedOrientation, setSelectedOrientation] = useState<string[]>([]);

	// Calculate min and max duration from facets
	const durationLimits = useMemo(() => {
		if (facetsData.durations && facetsData.durations.length > 0) {
			const min = Math.min(...facetsData.durations);
			const max = Math.max(...facetsData.durations);
			return { min, max };
		}
		return { min: 0, max: 300 }; // Default fallback
	}, [facetsData.durations]);

	// Initialize filters from URL on mount
	useEffect(() => {
		const categories =
			searchParams.get('categories')?.split(',').filter(Boolean) || [];
		const tags = searchParams.get('tags')?.split(',').filter(Boolean) || [];
		const locations =
			searchParams.get('locations')?.split(',').filter(Boolean) || [];
		const resolutions =
			searchParams.get('resolutions')?.split(',').filter(Boolean) || [];
		const orientations =
			searchParams.get('orientation')?.split(',').filter(Boolean) || [];
		const durationMin = searchParams.get('duration_min');
		const durationMax = searchParams.get('duration_max');
		const dateStart = searchParams.get('date_start');
		const dateEnd = searchParams.get('date_end');
		const sort = searchParams.get('sort');
		const view = searchParams.get('view');

		if (categories.length > 0) {
			setSelectedCategories(categories);
			setExpandedSections((prev) => ({ ...prev, categories: true }));
		} else if (category) {
			setSelectedCategories([category]);
			setExpandedSections((prev) => ({ ...prev, categories: true }));
		}

		if (tags.length > 0) {
			setSelectedTags(tags);
			setExpandedSections((prev) => ({ ...prev, tags: true }));
		}

		if (locations.length > 0) {
			setSelectedLocation(locations);
			setExpandedSections((prev) => ({ ...prev, location: true }));
		}

		if (resolutions.length > 0) {
			setSelectedResolution(resolutions);
			setExpandedSections((prev) => ({ ...prev, resolution: true }));
		}

		if (orientations.length > 0) {
			setSelectedOrientation(orientations);
			setExpandedSections((prev) => ({ ...prev, orientation: true }));
		}

		if (durationMin || durationMax) {
			setDurationRange([
				durationMin ? parseInt(durationMin) : 0,
				durationMax ? parseInt(durationMax) : 300,
			]);
			setExpandedSections((prev) => ({ ...prev, duration: true }));
		}

		if (dateStart || dateEnd) {
			setSelectedDateRange({
				start: dateStart || '',
				end: dateEnd || '',
			});
			setExpandedSections((prev) => ({ ...prev, dateRange: true }));
		}

		if (sort) setSortBy(sort);
		if (view === 'list' || view === 'grid') setViewMode(view);
	}, []);

	// Update URL whenever filters change
	const updateURL = useCallback(() => {
		const params = new URLSearchParams();

		// Add query if exists
		if (query) params.set('q', query);

		// Add filters
		if (selectedCategories.length > 0) {
			params.set('categories', selectedCategories.join(','));
		}
		if (selectedTags.length > 0) {
			params.set('tags', selectedTags.join(','));
		}
		if (selectedLocation.length > 0) {
			params.set('locations', selectedLocation.join(','));
		}
		if (selectedResolution.length > 0) {
			params.set('resolutions', selectedResolution.join(','));
		}
		if (selectedOrientation.length > 0) {
			params.set('orientation', selectedOrientation.join(','));
		}
		if (
			durationRange[0] > durationLimits.min ||
			durationRange[1] < durationLimits.max
		) {
			params.set('duration_min', durationRange[0].toString());
			params.set('duration_max', durationRange[1].toString());
		}
		if (selectedDateRange.start) {
			params.set('date_start', selectedDateRange.start);
		}
		if (selectedDateRange.end) {
			params.set('date_end', selectedDateRange.end);
		}
		if (sortBy !== 'relevance') {
			params.set('sort', sortBy);
		}
		if (viewMode !== 'grid') {
			params.set('view', viewMode);
		}
		if (currentPage > 1) {
			params.set('page', currentPage.toString());
		}

		const nextQuery = params.toString();
		const currentQuery = searchParams.toString();
		const newURL = nextQuery ? `${pathname}?${nextQuery}` : pathname;
		const currentURL = currentQuery ? `${pathname}?${currentQuery}` : pathname;
		if (newURL === currentURL) return;

		// Update URL without reload only when there is an actual diff.
		router.replace(newURL, { scroll: false });
	}, [
		query,
		selectedCategories,
		selectedTags,
		selectedLocation,
		selectedResolution,
		selectedOrientation,
		durationRange,
		durationLimits,
		selectedDateRange,
		sortBy,
		viewMode,
		currentPage,
		pathname,
		router,
		searchParams,
	]);

	// Update URL when filters change
	useEffect(() => {
		updateURL();
	}, [updateURL]);

	// Initialize duration range when facets data is loaded
	useEffect(() => {
		if (facetsData.durations && facetsData.durations.length > 0) {
			const urlDurationMin = searchParams.get('duration_min');
			const urlDurationMax = searchParams.get('duration_max');

			if (!urlDurationMin && !urlDurationMax) {
				setDurationRange([durationLimits.min, durationLimits.max]);
			}
		}
	}, [facetsData.durations, durationLimits]);

	const toggleSection = (section: keyof typeof expandedSections) => {
		setExpandedSections((prev) => ({
			...prev,
			[section]: !prev[section],
		}));
	};

	// Helper function to convert date string to YYYYMMDDHHmmssSSS format
	const convertDateToCustomFormat = (
		dateString: string,
		isEndOfDay: boolean = false
	): number => {
		const date = new Date(dateString);
		const year = date.getFullYear().toString();
		const month = (date.getMonth() + 1).toString().padStart(2, '0');
		const day = date.getDate().toString().padStart(2, '0');

		// For start of day: 000000000, for end of day: 235959999
		const time = isEndOfDay ? '235959999' : '000000000';

		const formattedDate = year + month + day + time;
		return parseInt(formattedDate);
	};

	const fetchFacets = async () => {
		try {
			const res = await axios.get(
				'http://localhost:5000/api/videos/facets',
				{
					headers: { 'x-api-key': 'key1' },
				}
			);

			if (res.data?.data?.facets) {
				const facets = res.data.data.facets;
				const rawAggs = res.data.data.raw_aggs;

				// Handle tags from raw_aggs which has the correct structure with doc_count
				const tagsData = rawAggs?.tags?.buckets || [];

				setFacetsData({
					locations: facets.locations || [],
					durations: facets.durations || [],
					created_dates: facets.created_dates || [],
					resolutions: facets.resolutions || [],
					orientation: facets.orientation || [],
					tags: tagsData,
				});
			}
		} catch (err) {
			console.error('Failed to fetch facets:', err);
		}
	};

	const fetchVideos = async (pageOverride?: number) => {
		setLoading(true);
		setError('');
		try {
			fetchAbortRef.current?.abort();
			const controller = new AbortController();
			fetchAbortRef.current = controller;

			const filtersPayload: Record<string, any> = {};

			if (selectedCategories.length > 0) {
				filtersPayload.categories = selectedCategories;
			}
			if (selectedTags.length > 0) {
				filtersPayload.tags = selectedTags;
			}
			if (
				durationRange[0] > durationLimits.min ||
				durationRange[1] < durationLimits.max
			) {
				filtersPayload.duration_min = durationRange[0];
				filtersPayload.duration_max = durationRange[1];
			}
			if (selectedDateRange.start) {
				filtersPayload.created_date_start = convertDateToCustomFormat(
					selectedDateRange.start,
					false
				);
			}
			if (selectedDateRange.end) {
				filtersPayload.created_date_end = convertDateToCustomFormat(
					selectedDateRange.end,
					true
				);
			}
			if (selectedLocation.length > 0) {
				filtersPayload.locations = selectedLocation;
			}
			if (selectedResolution.length > 0) {
				filtersPayload.resolutions = selectedResolution;
			}
			if (selectedOrientation.length > 0) {
				filtersPayload.orientation = selectedOrientation;
			}

			// The advanced-search API understands: relevance | newest | oldest | views | duration.
			// The legacy UI option "popular" maps to the server's "views" sort.
			const serverSortBy = sortBy === 'popular' ? 'views' : sortBy;
			const page = pageOverride ?? currentPage;

			const requestPayload = {
				query: query || '',
				filters: filtersPayload,
				sort: {
					by: serverSortBy,
					order: serverSortBy === 'oldest' ? 'asc' : 'desc',
				},
				pagination: {
					offset: (page - 1) * RESULTS_PER_PAGE,
					limit: RESULTS_PER_PAGE,
				},
			};

			const res = await axios.post(
				'/api/videos/advanced-search',
				requestPayload,
				{
					headers: { 'Content-Type': 'application/json' },
					signal: controller.signal,
				}
			);

			const payload = res.data?.data || {};
			const items = Array.isArray(payload.items) ? payload.items : [];

			// The advanced-search API returns [{video_id, document, scores}, ...].
			// Feed `document` into formatVideoData to reuse existing UI shapes.
			const formattedVideos = items
				.map((item: any) =>
					formatVideoData({
						...(item?.document || {}),
						video_id: item?.video_id || item?.document?.video_id,
					})
				)
				.filter(Boolean);

			setVideos(formattedVideos);
			setTotalResults(
				typeof payload.total === 'number' ? payload.total : formattedVideos.length
			);
			setExecution(payload.execution || null);
		} catch (err) {
			if (axios.isCancel(err)) return;
			setError('Failed to fetch videos');
			console.error('Advanced search error:', err);
		} finally {
			setLoading(false);
		}
	};

	const buildParsedIntent = useCallback(() => {
		const entities = query
			.split(/\s+/)
			.map((token) => token.trim().toLowerCase())
			.filter((token) => token.length > 2)
			.slice(0, 8);

		return {
			categories: selectedCategories,
			tags: selectedTags,
			entities,
			location: selectedLocation,
			resolution: selectedResolution,
			orientation: selectedOrientation,
		};
	}, [
		query,
		selectedCategories,
		selectedLocation,
		selectedOrientation,
		selectedResolution,
		selectedTags,
	]);

	const trackSearchEvent = useCallback(async () => {
		if (!isLoaded || !isSignedIn) return;
		const normalizedQuery = query.trim().replace(/\s+/g, ' ');
		if (!normalizedQuery) return;

		const keyPayload = {
			query: normalizedQuery,
			categories: selectedCategories,
			tags: selectedTags,
			location: selectedLocation,
			resolution: selectedResolution,
			orientation: selectedOrientation,
			durationRange,
			dateRange: selectedDateRange,
		};
		const nextKey = JSON.stringify(keyPayload);
		if (searchEventKeyRef.current === nextKey) return;

		try {
			const token = await getToken();
			if (!token) return;
			await ingestRecommendationSearchEvent(token, {
				query: normalizedQuery,
				parsed_intent: buildParsedIntent(),
			});
			searchEventKeyRef.current = nextKey;
		} catch (err) {
			console.error('Failed to ingest recommendation search event:', err);
		}
	}, [
		buildParsedIntent,
		durationRange,
		getToken,
		isLoaded,
		isSignedIn,
		query,
		selectedCategories,
		selectedDateRange,
		selectedLocation,
		selectedOrientation,
		selectedResolution,
		selectedTags,
	]);

	const trackClickEvent = useCallback(
		async (video: any) => {
			if (!isLoaded || !isSignedIn) return;
			try {
				const token = await getToken();
				if (!token || !video?.id) return;

				const categoryValue = video?.category;
				const categoriesPayload = Array.isArray(categoryValue)
					? categoryValue.filter((item) => typeof item === 'string')
					: typeof categoryValue === 'string' && categoryValue
					? [categoryValue]
					: [];

				await ingestRecommendationClickEvent(token, {
					video_id: video.id,
					event_type: 'click',
					event_context: {
						categories: categoriesPayload,
						tags: Array.isArray(video?.tags) ? video.tags : [],
					},
				});
			} catch (err) {
				console.error('Failed to ingest recommendation click event:', err);
			}
		},
		[getToken, isLoaded, isSignedIn]
	);

	// Fetch facets on component mount
	useEffect(() => {
		fetchFacets();
	}, []);

	// Reset to page 1 and refetch whenever filters, query, or sort change.
	useEffect(() => {
		const timer = setTimeout(() => {
			setCurrentPage(1);
			fetchVideos(1);
			void trackSearchEvent();
		}, 350);

		return () => clearTimeout(timer);
	}, [
		query,
		JSON.stringify(selectedCategories),
		JSON.stringify(selectedTags),
		durationRange[0],
		durationRange[1],
		selectedDateRange.start,
		selectedDateRange.end,
		JSON.stringify(selectedLocation),
		JSON.stringify(selectedResolution),
		JSON.stringify(selectedOrientation),
		sortBy,
		trackSearchEvent,
	]);

	// Refetch when paginating (server-side pagination).
	useEffect(() => {
		if (currentPage > 1) {
			fetchVideos(currentPage);
		}
	}, [currentPage]);

	// Handle category filter changes
	const handleCategoryChange = (categoryKey: string, checked: boolean) => {
		setSelectedCategories((prev) =>
			checked ? [...prev, categoryKey] : prev.filter((c) => c !== categoryKey)
		);
	};

	// Handle tag filter changes
	const handleTagChange = (tag: string, checked: boolean) => {
		setSelectedTags((prev) =>
			checked ? [...prev, tag] : prev.filter((t) => t !== tag)
		);
	};

	// Handle location filter changes
	const handleLocationChange = (location: string, checked: boolean) => {
		setSelectedLocation((prev) =>
			checked ? [...prev, location] : prev.filter((l) => l !== location)
		);
	};

	// Handle resolution filter changes
	const handleResolutionChange = (resolution: string, checked: boolean) => {
		setSelectedResolution((prev) =>
			checked ? [...prev, resolution] : prev.filter((r) => r !== resolution)
		);
	};

	// Handle orientation filter changes
	const handleOrientationChange = (orientation: string, checked: boolean) => {
		setSelectedOrientation((prev) =>
			checked ? [...prev, orientation] : prev.filter((o) => o !== orientation)
		);
	};

	// Handle date range changes
	const handleDateRangeChange = (field: 'start' | 'end', value: string) => {
		setSelectedDateRange((prev) => ({
			...prev,
			[field]: value,
		}));
	};

	// Clear date range
	const clearDateRange = () => {
		setSelectedDateRange({
			start: '',
			end: '',
		});
	};

	// Handle duration range change for min value
	const handleMinDurationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const minValue = Math.min(Number(e.target.value), durationRange[1] - 1);
		setDurationRange([minValue, durationRange[1]]);
	};

	// Handle duration range change for max value
	const handleMaxDurationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const maxValue = Math.max(Number(e.target.value), durationRange[0] + 1);
		setDurationRange([durationRange[0], maxValue]);
	};

	// Clear duration filter
	const clearDurationFilter = () => {
		setDurationRange([durationLimits.min, durationLimits.max]);
	};

	// Format seconds to minutes:seconds
	const formatDuration = (seconds: number) => {
		const mins = Math.floor(seconds / 60);
		const secs = seconds % 60;
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	};

	// Sorting and pagination are handled server-side by advanced-search.
	const currentResults = videos;
	const totalPages = Math.max(1, Math.ceil(totalResults / RESULTS_PER_PAGE));

	const goToPage = (page: number) => {
		setCurrentPage(page);
		window.scrollTo({ top: 0, behavior: 'smooth' });
	};

	const SectionHeader = ({
		title,
		sectionKey,
	}: {
		title: string;
		sectionKey: keyof typeof expandedSections;
	}) => (
		<div
			className='flex items-center justify-between cursor-pointer hover:text-blue-600 transition-colors'
			onClick={() => toggleSection(sectionKey)}
		>
			<h3 className='font-bold'>{title}</h3>
			{expandedSections[sectionKey] ? (
				<ChevronUp className='h-4 w-4' />
			) : (
				<ChevronDown className='h-4 w-4' />
			)}
		</div>
	);

	if (loading && videos.length === 0) {
		return (
			<div className='flex justify-center items-center py-12'>
				<div className='text-lg'>Loading videos...</div>
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
		<div className='flex gap-6'>
			{/* Sidebar */}
			<div className='flex flex-col'>
				<Button
					variant='outline'
					size='sm'
					onClick={() => setSidebarOpen(!sidebarOpen)}
					className='mb-4 self-start'
				>
					<Filter className='h-4 w-4 mr-2' />
					{sidebarOpen ? 'Hide Filters' : 'Show Filters'}
				</Button>

				{sidebarOpen && (
					<div className='w-64 flex-shrink-0 space-y-4 p-4 border rounded-lg max-h-[80vh] overflow-y-auto'>
						{/* Categories */}
						<div>
							<SectionHeader title='Categories' sectionKey='categories' />
							{expandedSections.categories && (
								<div className='space-y-1 mt-2 max-h-48 overflow-y-auto'>
									{categories.map((catObj) => (
										<div key={catObj.key}>
											<label className='flex items-center gap-2 hover:bg-gray-50 p-1 rounded cursor-pointer'>
												<input
													type='checkbox'
													value={catObj.key}
													checked={selectedCategories.includes(catObj.key)}
													onChange={(e) =>
														handleCategoryChange(catObj.key, e.target.checked)
													}
													className='cursor-pointer'
												/>
												<span className='text-sm'>
													{catObj.key} ({catObj.doc_count})
												</span>
											</label>
										</div>
									))}
								</div>
							)}
						</div>

						{/* Tags */}
						<div>
							<SectionHeader title='Tags' sectionKey='tags' />
							{expandedSections.tags && (
								<div className='space-y-1 mt-2 max-h-48 overflow-y-auto'>
									{facetsData.tags
										.filter(
											(tagObj) =>
												tagObj && tagObj.key && typeof tagObj.key === 'string'
										)
										.slice(0, 50)
										.map((tagObj) => (
											<div key={tagObj.key}>
												<label className='flex items-center gap-2 hover:bg-gray-50 p-1 rounded cursor-pointer'>
													<input
														type='checkbox'
														value={tagObj.key}
														checked={selectedTags.includes(tagObj.key)}
														onChange={(e) =>
															handleTagChange(tagObj.key, e.target.checked)
														}
														className='cursor-pointer'
													/>
													<span className='text-sm'>
														{tagObj.key.trim()} ({tagObj.doc_count || 0})
													</span>
												</label>
											</div>
										))}
								</div>
							)}
						</div>

						{/* Duration Range Slider */}
						<div>
							<SectionHeader title='Duration (seconds)' sectionKey='duration' />
							{expandedSections.duration && (
								<div className='space-y-4 mt-2'>
									<div className='text-center text-sm font-medium'>
										{durationRange[0]}s - {durationRange[1]}s
										<br />
										<span className='text-xs text-gray-500'>
											({formatDuration(durationRange[0])} -{' '}
											{formatDuration(durationRange[1])})
										</span>
									</div>

									{/* Min Duration Input */}
									<div className='space-y-2'>
										<label className='text-xs font-medium text-gray-700'>
											Min Duration: {durationRange[0]}s
										</label>
										<input
											type='range'
											min={durationLimits.min}
											max={durationLimits.max}
											value={durationRange[0]}
											onChange={handleMinDurationChange}
											className='w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer'
										/>
									</div>

									{/* Max Duration Input */}
									<div className='space-y-2'>
										<label className='text-xs font-medium text-gray-700'>
											Max Duration: {durationRange[1]}s
										</label>
										<input
											type='range'
											min={durationLimits.min}
											max={durationLimits.max}
											value={durationRange[1]}
											onChange={handleMaxDurationChange}
											className='w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer'
										/>
									</div>

									<div className='flex justify-between text-xs text-gray-500'>
										<span>{durationLimits.min}s</span>
										<span>{durationLimits.max}s</span>
									</div>

									{(durationRange[0] > durationLimits.min ||
										durationRange[1] < durationLimits.max) && (
										<Button
											variant='outline'
											size='sm'
											onClick={clearDurationFilter}
											className='w-full text-xs'
										>
											Clear Duration Filter
										</Button>
									)}
								</div>
							)}
						</div>

						{/* Date Range Picker */}
						<div>
							<SectionHeader title='Upload Date Range' sectionKey='dateRange' />
							{expandedSections.dateRange && (
								<div className='space-y-3 mt-2'>
									<div className='space-y-2'>
										<label className='text-xs font-medium text-gray-700 flex items-center gap-1'>
											<Calendar className='h-3 w-3' />
											From Date
										</label>
										<input
											type='date'
											value={selectedDateRange.start}
											onChange={(e) =>
												handleDateRangeChange('start', e.target.value)
											}
											className='w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
										/>
									</div>
									<div className='space-y-2'>
										<label className='text-xs font-medium text-gray-700 flex items-center gap-1'>
											<Calendar className='h-3 w-3' />
											To Date
										</label>
										<input
											type='date'
											value={selectedDateRange.end}
											onChange={(e) =>
												handleDateRangeChange('end', e.target.value)
											}
											className='w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
										/>
									</div>
									{(selectedDateRange.start || selectedDateRange.end) && (
										<Button
											variant='outline'
											size='sm'
											onClick={clearDateRange}
											className='w-full text-xs'
										>
											Clear Date Range
										</Button>
									)}
									{(selectedDateRange.start || selectedDateRange.end) && (
										<div className='text-xs text-gray-500 p-2 bg-gray-50 rounded'>
											{selectedDateRange.start && selectedDateRange.end ? (
												<span>
													Showing videos from {selectedDateRange.start} to{' '}
													{selectedDateRange.end}
												</span>
											) : selectedDateRange.start ? (
												<span>
													Showing videos from {selectedDateRange.start} onwards
												</span>
											) : (
												<span>
													Showing videos until {selectedDateRange.end}
												</span>
											)}
										</div>
									)}
								</div>
							)}
						</div>

						{/* Locations */}
						{facetsData.locations.length > 0 && (
							<div>
								<SectionHeader title='Location' sectionKey='location' />
								{expandedSections.location && (
									<div className='space-y-1 mt-2 max-h-32 overflow-y-auto'>
										{facetsData.locations.map((location) => (
											<div key={location}>
												<label className='flex items-center gap-2 hover:bg-gray-50 p-1 rounded cursor-pointer'>
													<input
														type='checkbox'
														value={location}
														checked={selectedLocation.includes(location)}
														onChange={(e) =>
															handleLocationChange(location, e.target.checked)
														}
														className='cursor-pointer'
													/>
													<span className='text-sm'>{location}</span>
												</label>
											</div>
										))}
									</div>
								)}
							</div>
						)}

						{/* Resolutions */}
						{facetsData.resolutions.length > 0 && (
							<div>
								<SectionHeader title='Resolution' sectionKey='resolution' />
								{expandedSections.resolution && (
									<div className='space-y-1 mt-2'>
										{facetsData.resolutions.map((resolution) => (
											<div key={resolution}>
												<label className='flex items-center gap-2 hover:bg-gray-50 p-1 rounded cursor-pointer'>
													<input
														type='checkbox'
														value={resolution}
														checked={selectedResolution.includes(resolution)}
														onChange={(e) =>
															handleResolutionChange(
																resolution,
																e.target.checked
															)
														}
														className='cursor-pointer'
													/>
													<span className='text-sm'>{resolution}</span>
												</label>
											</div>
										))}
									</div>
								)}
							</div>
						)}

						{/* Orientation */}
						{facetsData.orientation.length > 0 && (
							<div>
								<SectionHeader title='Orientation' sectionKey='orientation' />
								{expandedSections.orientation && (
									<div className='space-y-1 mt-2'>
										{facetsData.orientation.map((orientation) => (
											<div key={orientation}>
												<label className='flex items-center gap-2 hover:bg-gray-50 p-1 rounded cursor-pointer'>
													<input
														type='checkbox'
														value={orientation}
														checked={selectedOrientation.includes(orientation)}
														onChange={(e) =>
															handleOrientationChange(
																orientation,
																e.target.checked
															)
														}
														className='cursor-pointer'
													/>
													<span className='text-sm capitalize'>
														{orientation}
													</span>
												</label>
											</div>
										))}
									</div>
								)}
							</div>
						)}
					</div>
				)}
			</div>

			{/* Main Results */}
			<div className='flex-1 space-y-6'>
				{/* Results Header */}
				<div className='flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4'>
					<div className='space-y-2'>
						<h2 className='text-2xl font-bold'>
							{query
								? `Search Results for "${query}"`
								: selectedCategories.length > 0
								? `${selectedCategories.join(', ')} Videos`
								: 'Browse Videos'}
						</h2>
						<p className='text-muted-foreground'>
							{totalResults.toLocaleString()} videos found
							{(selectedCategories.length > 0 ||
								selectedTags.length > 0 ||
								selectedLocation.length > 0 ||
								selectedResolution.length > 0 ||
								selectedOrientation.length > 0 ||
								durationRange[0] > durationLimits.min ||
								durationRange[1] < durationLimits.max ||
								selectedDateRange.start ||
								selectedDateRange.end) && (
								<span className='ml-2 text-blue-600'>
									(with filters applied)
								</span>
							)}
							{execution?.total_ms !== undefined && (
								<span className='ml-2 text-xs text-muted-foreground'>
									· {execution.total_ms} ms
								</span>
							)}
						</p>
					</div>

					<div className='flex items-center gap-4'>
						<div className='flex border rounded-lg p-1'>
							<Button
								variant={viewMode === 'grid' ? 'default' : 'ghost'}
								size='sm'
								onClick={() => setViewMode('grid')}
							>
								<Grid3X3 className='h-4 w-4' />
							</Button>
							<Button
								variant={viewMode === 'list' ? 'default' : 'ghost'}
								size='sm'
								onClick={() => setViewMode('list')}
							>
								<List className='h-4 w-4' />
							</Button>
						</div>

						<Select value={sortBy} onValueChange={setSortBy}>
							<SelectTrigger className='w-40'>
								<SelectValue placeholder='Sort by' />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value='relevance'>Relevance</SelectItem>
								<SelectItem value='newest'>Newest First</SelectItem>
								<SelectItem value='oldest'>Oldest First</SelectItem>
								<SelectItem value='popular'>Most Popular</SelectItem>
								<SelectItem value='duration'>Duration</SelectItem>
							</SelectContent>
						</Select>
					</div>
				</div>

				{/* Results Grid */}
				<div
					className={
						viewMode === 'grid'
							? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'
							: 'space-y-4'
					}
				>
					{currentResults.map((video) => (
						<VideoCard key={video.id} video={video} onOpen={trackClickEvent} />
					))}
				</div>

				{/* Empty State */}
				{totalResults === 0 && !loading && (
					<div className='text-center py-12'>
						<p className='text-muted-foreground'>
							No videos found matching your criteria.
						</p>
					</div>
				)}

				{/* Pagination */}
				{totalPages > 1 && (
					<div className='flex justify-center items-center space-x-4 pt-8'>
						<Button
							variant='outline'
							onClick={() => goToPage(currentPage - 1)}
							disabled={currentPage === 1}
						>
							<ChevronLeft className='h-4 w-4 mr-1' />
							Previous
						</Button>

						<div className='flex space-x-2'>
							{Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
								let page;
								if (totalPages <= 5) {
									page = i + 1;
								} else if (currentPage <= 3) {
									page = i + 1;
								} else if (currentPage >= totalPages - 2) {
									page = totalPages - 4 + i;
								} else {
									page = currentPage - 2 + i;
								}

								return (
									<Button
										key={page}
										variant={currentPage === page ? 'default' : 'outline'}
										size='sm'
										onClick={() => goToPage(page)}
										className='w-10'
									>
										{page}
									</Button>
								);
							})}
						</div>

						<Button
							variant='outline'
							onClick={() => goToPage(currentPage + 1)}
							disabled={currentPage === totalPages}
						>
							Next
							<ChevronRight className='h-4 w-4 ml-1' />
						</Button>
					</div>
				)}
			</div>
		</div>
	);
});

SearchResults.displayName = 'SearchResults';
