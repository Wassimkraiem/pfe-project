import Link from 'next/link';
import { ArrowRight, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';

const highlights = [
	'Approved for monetization',
	'Watermark-free downloads',
	'Unlimited monthly access',
];

const features = [
	'Fast-growing channel workflows',
	'Commercial-ready licensing',
	'Meta data and source details',
	'Priority support for creators',
];

export function SignupSpotlight() {
	return (
		<section className='rounded-3xl border border-[#dbeafe] bg-gradient-to-br from-[#eff6ff] via-white to-[#f8fbff] p-6 md:p-10'>
			<div className='grid gap-10 lg:grid-cols-2 lg:items-center'>
				<div className='space-y-6'>
					<p className='text-sm font-semibold uppercase tracking-[0.16em] text-[#4D8AFF]'>
						Over 90,000+ viral-proven videos
					</p>
					<div className='space-y-4'>
						<h2 className='text-3xl md:text-4xl font-bold tracking-tight text-[#111827]'>
							Affordable pricing.
							<br />
							Easy scaling.
						</h2>
						<p className='max-w-xl text-base md:text-lg text-[#4b5563]'>
							Start your BVIRAL membership from the dashboard and unlock a
							complete video library built for growth.
						</p>
					</div>
					<div className='space-y-3'>
						{highlights.map((item) => (
							<div key={item} className='flex items-center gap-2 text-[#111827]'>
								<Check className='h-4 w-4 text-[#4D8AFF]' />
								<span className='font-medium'>{item}</span>
							</div>
						))}
					</div>
				</div>

				<div className='rounded-3xl bg-[#4D8AFF] text-white p-6 md:p-8 shadow-lg shadow-[#4D8AFF]/25'>
					<div className='space-y-1'>
						<p className='text-sm uppercase tracking-[0.12em] text-white/85'>
							Creator plan
						</p>
						<p className='text-5xl font-bold'>
							$399<span className='text-xl font-semibold'>/month</span>
						</p>
						<p className='text-sm text-white/90'>
							For channels with less than 2M followers
						</p>
					</div>

					<Button
						asChild
						size='lg'
						className='mt-6 w-full rounded-full bg-white text-[#4D8AFF] hover:bg-white/90'
					>
						<Link href='/sign-up'>
							Get Started Now
							<ArrowRight className='ml-2 h-4 w-4' />
						</Link>
					</Button>

					<div className='mt-6 space-y-2'>
						{features.map((feature) => (
							<div key={feature} className='flex items-center gap-2 text-sm'>
								<span className='h-2 w-2 rounded-full bg-white' />
								<span>{feature}</span>
							</div>
						))}
					</div>
				</div>
			</div>
		</section>
	);
}
