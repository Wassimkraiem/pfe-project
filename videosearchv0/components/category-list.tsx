'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';
import { ArrowRight, Tag } from 'lucide-react';

type Category = {
	key: string;
	doc_count: number;
};

export function CategoryList() {
	const router = useRouter();
	const [categories, setCategories] = useState<Category[]>([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		const fetchCategories = async () => {
			try {
				const res = await fetch(
					'http://localhost:5000/api/videos/categories',
					{ headers: { 'x-api-key': 'key1' } }
				);
				const data = await res.json();
				setCategories(data.data.buckets || []);
			} catch (error) {
				console.error('Failed to fetch categories:', error);
			} finally {
				setLoading(false);
			}
		};

		fetchCategories();
	}, []);

	const handleCategoryClick = (categoryId: string) => {
		router.push(`/search?category=${encodeURIComponent(categoryId)}`);
	};

	if (loading) {
		return <p className='text-muted-foreground'>Loading categories...</p>;
	}

	return (
		<div className='space-y-4'>
			{categories.map((category) => {
				return (
					<Card
						key={category.key}
						className='group cursor-pointer hover:shadow-lg transition-all duration-300'
						onClick={() => handleCategoryClick(category.key)}
					>
						<CardContent className='p-6'>
							<div className='flex items-center justify-between'>
								<div className='flex items-center space-x-4'>
									<div
										className={`w-12 h-12 bg-primary rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300`}
									>
										<Tag className='h-6 w-6 text-white' />
									</div>
									<div className='space-y-1'>
										<h3 className='font-semibold text-lg group-hover:text-primary transition-colors'>
											{category.key}
										</h3>
										<p className='text-sm text-muted-foreground'>
											{category.doc_count} videos
										</p>
									</div>
								</div>

								<div className='flex items-center space-x-4'>
									<div className='text-right'>
										<Badge variant='secondary' className='text-sm'>
											{category.doc_count.toLocaleString()} videos
										</Badge>
									</div>
									<Button
										variant='ghost'
										size='sm'
										className='opacity-0 group-hover:opacity-100 transition-opacity duration-300'
									>
										<ArrowRight className='h-4 w-4' />
									</Button>
								</div>
							</div>
						</CardContent>
					</Card>
				);
			})}
		</div>
	);
}
