'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useRouter } from 'next/navigation';
import {
	Tag,
	Utensils,
	Dumbbell,
	Laugh,
	Sparkles,
	Heart,
	Wine,
	Hammer,
	Sun,
	TrendingDown,
	Snowflake,
	Plane,
	Scissors,
} from 'lucide-react';

type Category = {
	key: string;
	doc_count: number;
};

type CategoryGridProps = {
	categories: Category[];
};

export function CategoryGrid({ categories }: CategoryGridProps) {
	const router = useRouter();

	const handleCategoryClick = (categoryName: string, count: number) => {
		router.push(
			`/search?category=${encodeURIComponent(
				categoryName
			)}&count=${encodeURIComponent(count)}`
		);
	};

	// Icon mapping for your categories
	const iconMap: Record<string, any> = {
		Cool: Snowflake,
		Travel: Plane,
		Crafty: Scissors,
		'Gym/Workout': Dumbbell,
		Animals: Tag,
		Comedy: Laugh,
		Food: Utensils,
		Sports: Dumbbell,
		Fails: TrendingDown,
		Beauty: Sparkles,
		Feels: Heart,
		Boozy: Wine,
		DIY: Hammer,
		'Feel good': Heart,
		Weather: Sun,
	};

	if (!categories || categories.length === 0) {
		return <p className='text-muted-foreground'>No categories found.</p>;
	}

	return (
		<div className='grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6'>
			{categories.map((category) => {
				const Icon = iconMap[category.key] || Tag;
				return (
					<Card
						key={category.key}
						className='group cursor-pointer hover:shadow-lg transition-all duration-300 hover:-translate-y-1'
						onClick={() =>
							handleCategoryClick(category.key, category.doc_count)
						}
					>
						<CardContent className='p-6 text-center space-y-4'>
							<div className='w-16 h-16 bg-primary rounded-2xl flex items-center justify-center mx-auto group-hover:scale-110 transition-transform duration-300'>
								<Icon className='h-8 w-8 text-black' />
							</div>
							<div className='space-y-2'>
								<h3 className='font-semibold text-lg group-hover:text-primary transition-colors'>
									{category.key}
								</h3>
								<Badge variant='secondary' className='text-xs'>
									{category.doc_count.toLocaleString()} videos
								</Badge>
							</div>
						</CardContent>
					</Card>
				);
			})}
		</div>
	);
}
