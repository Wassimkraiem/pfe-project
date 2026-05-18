'use client';
import { Suspense } from 'react';
import { CategoryGrid } from '@/components/category-grid';
import { LatestVideos } from '@/components/latest-videos';
import { Hero } from '@/components/hero';
import { SignupSpotlight } from '@/components/signup-spotlight';
import { BviralLandingClone } from '@/components/bviral-landing-clone';
import { RecommendationsSection } from '@/components/recommendations-section';
import { useCategories } from './context/CategoriesContext';
import { useAuth } from '@clerk/nextjs';

export default function HomePage() {
	const { categories } = useCategories();
	const { isLoaded, isSignedIn } = useAuth();
	const shouldShowMarketingSections = !isLoaded || !isSignedIn;

	return (
		<div className='min-h-screen bg-background'>
			<Hero />

			<main className='container mx-auto px-4 py-8 md:py-10 space-y-10'>
				<RecommendationsSection />

				{/* Categories Section */}
				<section id='categories-section' className='space-y-8'>
					<div className='text-center space-y-4'>
						<h2 className='text-3xl font-bold tracking-tight'>
							Browse by Category
						</h2>
						<p className='text-muted-foreground text-lg max-w-2xl mx-auto'>
							Explore our curated collection organized by themes and topics
						</p>
					</div>
					<CategoryGrid categories={categories} />
				</section>

				{/* Latest Videos Section */}
				<section className='space-y-8'>
					<div className='text-center space-y-4'>
						<h2 className='text-3xl font-bold tracking-tight'>
							Latest Additions
						</h2>
						<p className='text-muted-foreground text-lg max-w-2xl mx-auto'>
							Check out the newest videos added to our collection
						</p>
					</div>
					<Suspense
						fallback={<div className='text-center py-8'>Loading videos...</div>}
					>
						<LatestVideos />
					</Suspense>
				</section>

				{shouldShowMarketingSections && (
					<section className='space-y-6'>
						<div className='text-center space-y-3'>
							<h2 className='text-3xl font-bold tracking-tight'>Join BVIRAL</h2>
							<p className='text-muted-foreground text-lg max-w-2xl mx-auto'>
								Create your account to unlock licensing, downloads, and full
								creator tools.
							</p>
						</div>
						<SignupSpotlight />
					</section>
				)}
			</main>

			{shouldShowMarketingSections && <BviralLandingClone />}
		</div>
	);
}
