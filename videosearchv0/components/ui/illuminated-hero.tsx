import React from 'react';
import Link from 'next/link';
import { Search, Library } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { SearchBar } from '@/components/search-bar';

export function IlluminatedHero() {
	return (
		<div className='relative w-full flex min-h-[78vh] flex-wrap items-center justify-center overflow-hidden bg-gradient-to-b from-[#0b1b4d] via-[#133c9b] to-[#0f2d78] text-[calc(var(--size)*0.022)] text-white [--factor:min(1000px,100vh)] [--size:min(var(--factor),100vw)]'>
			<div className='absolute h-full w-full max-w-[44em]'>
				<div className='shadow-bgt absolute size-full translate-[0_-70%] scale-[1.2] animate-[onloadbgt_1s_ease-in-out_forwards] rounded-[100em] opacity-60' />
				<div className='shadow-bgb absolute size-full translate-[0_-70%] scale-[1.2] animate-[onloadbgb_1s_ease-in-out_forwards] rounded-[100em] opacity-60' />
			</div>

			<div className='absolute inset-0 bg-[radial-gradient(circle_at_25%_10%,rgba(147,197,253,0.3),transparent_45%),radial-gradient(circle_at_80%_80%,rgba(191,219,254,0.22),transparent_45%)]' />

			<div className='relative z-10 container mx-auto px-4 py-14 lg:py-16'>
				<div className='max-w-4xl mx-auto text-center space-y-6'>
					<div className='text-4xl md:text-5xl font-semibold' aria-hidden='true'>
						Discover
						<br />
						<span
							className={cn(
								'relative inline-block',
								'before:absolute before:animate-[onloadopacity_1s_ease-out_forwards] before:opacity-0 before:content-[attr(data-text)]',
								'before:bg-[linear-gradient(0deg,#dbeafe_0%,#ffffff_50%)] before:bg-clip-text before:text-[#eff6ff]',
								'filter-[url(#glow-4)]'
							)}
							data-text='Amazing Videos.'
						>
							Amazing Videos.
						</span>
						<br />
						For Your Next Project.
					</div>

					<p className='max-w-[36em] mx-auto text-center font-semibold text-blue-100/95 text-base md:text-lg'>
						Search, license, and download high-performing clips built to scale
						your content output.
					</p>

					<div className='space-y-4'>
						<SearchBar />
						<div className='flex flex-col sm:flex-row gap-4 justify-center items-center'>
							<Button
								size='lg'
								className='h-12 px-8 text-base min-w-[200px] bg-white text-[#1d4ed8] hover:bg-blue-50'
								asChild
							>
								<Link href='/search'>
									<Search className='mr-2 h-5 w-5' />
									Search for Video
								</Link>
							</Button>
							<Button
								variant='outline'
								size='lg'
								className='h-12 px-8 text-base min-w-[200px] border-blue-200 text-white hover:bg-white/10 bg-transparent'
								asChild
							>
								<Link href='/search'>
									<Library className='mr-2 h-5 w-5' />
									Explore Library
								</Link>
							</Button>
						</div>
					</div>
				</div>
			</div>

			<svg
				className='absolute z-[-1] h-0 w-0'
				width='1440px'
				height='300px'
				viewBox='0 0 1440 300'
				xmlns='http://www.w3.org/2000/svg'
			>
				<defs>
					<filter
						id='glow-4'
						colorInterpolationFilters='sRGB'
						x='-50%'
						y='-200%'
						width='200%'
						height='500%'
					>
						<feGaussianBlur in='SourceGraphic' stdDeviation='4' result='blur4' />
						<feGaussianBlur in='SourceGraphic' stdDeviation='19' result='blur19' />
						<feGaussianBlur in='SourceGraphic' stdDeviation='9' result='blur9' />
						<feGaussianBlur in='SourceGraphic' stdDeviation='30' result='blur30' />
						<feColorMatrix
							in='blur4'
							result='color-0-blur'
							type='matrix'
							values='1 0 0 0 0 0 0.98 0 0 0 0 0 0.96 0 0 0 0 0 0.8 0'
						/>
						<feOffset in='color-0-blur' result='layer-0-offsetted' dx='0' dy='0' />
						<feColorMatrix
							in='blur19'
							result='color-1-blur'
							type='matrix'
							values='0.35 0 0 0 0 0 0.60 0 0 0 0 0 1 0 0 0 0 0 1 0'
						/>
						<feOffset in='color-1-blur' result='layer-1-offsetted' dx='0' dy='2' />
						<feColorMatrix
							in='blur9'
							result='color-2-blur'
							type='matrix'
							values='0.50 0 0 0 0 0 0.72 0 0 0 0 0 1 0 0 0 0 0 0.65 0'
						/>
						<feOffset in='color-2-blur' result='layer-2-offsetted' dx='0' dy='2' />
						<feMerge>
							<feMergeNode in='layer-0-offsetted' />
							<feMergeNode in='layer-1-offsetted' />
							<feMergeNode in='layer-2-offsetted' />
							<feMergeNode in='SourceGraphic' />
						</feMerge>
					</filter>
				</defs>
			</svg>
		</div>
	);
}
