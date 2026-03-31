'use client';

import { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';
import { SearchResults } from '@/components/search-results';

export default function SearchPage() {
	const searchParams = useSearchParams();
	const category = searchParams.get('category') || '';
	const count = searchParams.get('count') || '';
	const [searchQuery, setSearchQuery] = useState(searchParams.get('q') || '');
	console.log(category);
	const handleSearchSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		// Optionally, update the URL or trigger re-fetch in SearchResults
	};

	return (
		<div className='min-h-screen bg-background'>
			{/* Sticky Search Bar */}
			<div className='border-b bg-background/95 backdrop-blur sticky top-0 z-50'>
				<div className='container mx-auto px-4 py-4'>
					<form
						className='flex gap-4 items-center'
						onSubmit={handleSearchSubmit}
					>
						<div className='flex-1 relative'>
							<Search className='absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4' />
							<Input
								type='search'
								placeholder='Search videos...'
								value={searchQuery}
								onChange={(e) => setSearchQuery(e.target.value)}
								className='pl-10 h-12 text-base'
							/>
						</div>
						<Button type='submit' size='lg' className='h-12 px-8'>
							Search
						</Button>
					</form>
				</div>
			</div>

			{/* Results */}
			<div className='container mx-auto px-4 py-8'>
				<SearchResults query={searchQuery} category={category} count={count} />
			</div>
		</div>
	);
}
