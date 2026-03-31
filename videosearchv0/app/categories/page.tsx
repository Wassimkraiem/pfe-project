'use client';

import { useState } from 'react';
import { CategoryGrid } from '@/components/category-grid';
import { useCategories } from '../context/CategoriesContext';
import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';

export default function CategoriesPage() {
	const { categories } = useCategories();
	const [searchTerm, setSearchTerm] = useState('');

	// Filter categories based on search term (case-insensitive)
	const filteredCategories = categories.filter((cat) =>
		cat.key.toLowerCase().includes(searchTerm.toLowerCase())
	);

	return (
		<div className='min-h-screen bg-background'>
			{/* ...breadcrumb and header code unchanged... */}

			{/* Search Bar */}
			<div className='container mx-auto px-4 py-8'>
				<div className='relative max-w-md mx-auto mb-8'>
					<Search className='absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4' />
					<Input
						type='search'
						placeholder='Search categories...'
						className='pl-10'
						value={searchTerm}
						onChange={(e) => setSearchTerm(e.target.value)}
					/>
				</div>

				{/* Categories Grid */}
				<CategoryGrid categories={filteredCategories} />

				{/* Category Statistics */}
				<div className='mt-16 bg-muted/30 rounded-2xl p-8'>
					<div className='text-center space-y-4 mb-8'>
						<h2 className='text-2xl font-bold'>Category Overview</h2>
						<p className='text-muted-foreground'>
							Discover the breadth of our video library across different
							categories
						</p>
					</div>
					<div className='grid grid-cols-2 md:grid-cols-4 gap-6'>
						<div className='text-center space-y-2'>
							<div className='text-3xl font-bold text-primary'>
								{filteredCategories.length}
							</div>
							<div className='text-sm text-muted-foreground'>
								Total Categories
							</div>
						</div>
						<div className='text-center space-y-2'>
							<div className='text-3xl font-bold text-primary'>
								{filteredCategories
									.reduce((acc, c) => acc + c.doc_count, 0)
									.toLocaleString()}
							</div>
							<div className='text-sm text-muted-foreground'>Total Videos</div>
						</div>
						<div className='text-center space-y-2'>
							<div className='text-3xl font-bold text-primary'>
								{Math.max(
									...filteredCategories.map((c) => c.doc_count),
									0
								).toLocaleString()}
							</div>
							<div className='text-sm text-muted-foreground'>Most Popular</div>
						</div>
						<div className='text-center space-y-2'>
							<div className='text-3xl font-bold text-primary'>
								{filteredCategories[
									filteredCategories.length - 1
								]?.doc_count?.toLocaleString() ?? 0}
							</div>
							<div className='text-sm text-muted-foreground'>
								Newest Category
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
