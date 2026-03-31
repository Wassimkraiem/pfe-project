import Link from 'next/link';
import {
	ArrowRight,
	Check,
	Quote,
	ShieldCheck,
	Sparkles,
	TrendingUp,
	Users,
	Video,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
	Accordion,
	AccordionContent,
	AccordionItem,
	AccordionTrigger,
} from '@/components/ui/accordion';

const featureRows = [
	{
		title: 'Turn videos into',
		highlight: 'value...',
		text: 'Whether you are a video owner looking to go viral, a creator seeking to maximize long-term value, or a brand in need of rights-cleared, high-performing content, BVIRAL is the trusted partner for scalable impact.',
		cta: 'Let’s Talk',
		imagePosition: 'right',
		image: 'https://bviral.com/wp-content/uploads/2025/05/homepage1.webp',
	},
	{
		title: 'Boost following and',
		highlight: 'elevate your brand.',
		text: 'We help content creators and brands get seen by the right audience and turn visibility into measurable outcomes.',
		cta: 'See What’s Possible',
		imagePosition: 'left',
		image: 'https://bviral.com/wp-content/uploads/2025/05/homepage2.webp',
	},
	{
		title: 'Enjoy the benefits',
		highlight: 'without lifting a finger',
		text: 'We handle distribution, rights protection, syndication, and clearances so your team can focus on creating.',
		cta: 'Partner with BVIRAL',
		imagePosition: 'right',
		image: 'https://bviral.com/wp-content/uploads/2025/05/homepage3-1.webp',
	},
];

const creatorQuotes = [
	{
		handle: '@i_am_drogo_official',
		image: 'https://bviral.com/wp-content/uploads/2025/05/i_am_drogo_official.webp',
		text: 'I have been working with BVIRAL for a while now and they are easy to communicate with, kind, understanding, and responsive.',
	},
	{
		handle: '@chantychanterelle',
		image: 'https://bviral.com/wp-content/uploads/2025/05/chantychanterelle.webp',
		text: 'I have been working with BVIRAL for a few months. Their team is responsive and clear whenever I have questions.',
	},
	{
		handle: '@rugzart_official',
		image: 'https://bviral.com/wp-content/uploads/2025/05/rugzart.webp',
		text: 'BVIRAL has already posted multiple videos from my library. It helped me reach more followers and gave my videos new visibility.',
	},
	{
		handle: '@henriquejungers',
		image: 'https://bviral.com/wp-content/uploads/2025/05/henriquejungers.webp',
		text: 'The experience was really good. The team gave full attention during the process and communication stayed quick and consistent.',
	},
	{
		handle: '@countrylifeat71',
		image: 'https://bviral.com/wp-content/uploads/2025/05/countrylifeat71.webp',
		text: 'The process was simple and straightforward. I was informed at each step and it allowed my content to be seen by many more people.',
	},
];

const articles = [
	{
		title:
			'Beyond the Feed: Why Multi-Platform Distribution is the Future of Creator Growth',
		href: 'https://bviral.com/beyond-the-feed-why-multi-platform-distribution-is-the-future-of-creator-growth/',
		image: 'https://bviral.com/wp-content/uploads/2025/05/nt1-768x501.webp',
		excerpt:
			'The digital content economy is evolving fast, and platform diversification is now essential.',
	},
	{
		title: 'Here’s What You Get When You License a Video with BVIRAL',
		href: 'https://bviral.com/heres-what-you-get-when-you-license-a-video-with-bviral/',
		image: 'https://bviral.com/wp-content/uploads/2025/05/art8-768x501.webp',
		excerpt:
			'Access larger audiences, stronger protections, and licensing workflows built for creators.',
	},
	{
		title:
			'Why the Creator Economy Is Bleeding Billions—and What Smart Creators Are Doing About It',
		href: 'https://bviral.com/why-the-creator-economy-is-bleeding-billions-and-what-smart-creators-are-doing-about-it/',
		image: 'https://bviral.com/wp-content/uploads/2025/05/art7-768x501.webp',
		excerpt:
			'Your content is valuable, and better rights management is key to protecting that value.',
	},
];

const serviceItems = [
	'Strategic Video Distribution & Syndication',
	'Creator Support & Monetization Services',
	'Video IP & Rights Management (IPSHIELD)',
	'Access Our Viral Video Library',
];

function FeatureVisual({ image, title }: { image: string; title: string }) {
	return (
		<div className='relative min-h-[260px] rounded-2xl border border-[#d8e7ff] overflow-hidden bg-white'>
			<img
				src={image}
				alt={title}
				className='h-full w-full object-cover'
				loading='lazy'
			/>
		</div>
	);
}

export function BviralLandingClone() {
	return (
		<section className='bg-[#f6f7f9] border-b'>
			<div className='container mx-auto max-w-6xl px-4 py-10 md:py-14 space-y-12'>
				<div className='space-y-12'>
					{featureRows.map((row, index) => (
						<div
							key={row.title}
							className='grid gap-6 lg:grid-cols-2 lg:items-center'
						>
							{row.imagePosition === 'left' && (
								<FeatureVisual image={row.image} title={`${row.title} ${row.highlight}`} />
							)}
							<div className='space-y-4'>
								<h2 className='text-3xl md:text-4xl font-bold leading-tight text-[#101828]'>
									{row.title}{' '}
									<span className='bg-gradient-to-r from-[#4D8AFF] to-[#7c3aed] bg-clip-text text-transparent'>
										{row.highlight}
									</span>
								</h2>
								<p className='text-sm md:text-base text-[#667085] max-w-xl'>{row.text}</p>
								<Button asChild className='rounded-full px-6'>
									<Link href='/sign-up'>
										{row.cta}
										<ArrowRight className='ml-2 h-4 w-4' />
									</Link>
								</Button>
							</div>
							{row.imagePosition === 'right' && (
								<FeatureVisual image={row.image} title={`${row.title} ${row.highlight}`} />
							)}
						</div>
					))}
				</div>

				<div className='space-y-6'>
					<h3 className='text-3xl md:text-4xl font-bold text-center text-[#101828]'>
						See what our{' '}
						<span className='bg-gradient-to-r from-[#4D8AFF] to-[#7c3aed] bg-clip-text text-transparent'>
							creators
						</span>{' '}
						have to say...
					</h3>
					<div className='grid gap-3 md:grid-cols-2 xl:grid-cols-5'>
						{creatorQuotes.map((quote) => (
							<div
								key={quote.handle}
								className='rounded-xl bg-white p-4 border shadow-sm'
							>
								<Quote className='h-5 w-5 text-[#4D8AFF] mb-3' />
								<p className='text-sm text-[#475467]'>{quote.text}</p>
								<div className='mt-4 flex items-center gap-2'>
									<img
										src={quote.image}
										alt={quote.handle}
										className='h-7 w-7 rounded-full object-cover'
										loading='lazy'
									/>
									<p className='text-xs text-[#667085]'>{quote.handle}</p>
								</div>
							</div>
						))}
					</div>
				</div>

				<div className='space-y-6'>
					<h3 className='text-3xl md:text-4xl font-bold text-center text-[#101828]'>
						Ready to read...
					</h3>
					<div className='grid gap-4 md:grid-cols-3'>
						{articles.map((article) => (
							<div
								key={article.href}
								className='rounded-2xl overflow-hidden border bg-white'
							>
								<a href={article.href} target='_blank' rel='noopener noreferrer'>
									<img
										src={article.image}
										alt={article.title}
										className='h-32 md:h-36 w-full object-cover'
										loading='lazy'
									/>
								</a>
								<div className='p-4 space-y-3'>
									<p className='font-semibold text-sm text-[#101828]'>
										{article.title}
									</p>
									<p className='text-xs text-[#667085]'>{article.excerpt}</p>
									<a
										href={article.href}
										target='_blank'
										rel='noopener noreferrer'
										className='text-sm font-semibold text-[#101828]'
									>
										Read article
									</a>
								</div>
							</div>
						))}
					</div>
				</div>

				<div className='bg-white rounded-3xl border p-5 md:p-8 space-y-6'>
					<h3 className='text-3xl md:text-4xl font-bold text-center text-[#101828]'>
						Get started with the right service.
					</h3>
					<div className='grid gap-6 lg:grid-cols-2 lg:items-center'>
						<div className='min-h-[220px] rounded-2xl border overflow-hidden bg-white'>
							<img
								src='https://bviral.com/wp-content/uploads/2025/05/homepageservices1-1-1-1024x880.webp'
								alt='Get started with the right service'
								className='h-full w-full object-cover'
								loading='lazy'
							/>
						</div>
						<div className='space-y-4'>
							<div className='flex gap-4 text-xs font-semibold text-[#667085] uppercase tracking-wide'>
								<span className='text-[#101828]'>Creators</span>
								<span>Submit a Video</span>
								<span>Get Viral Clips</span>
							</div>
							<h4 className='text-2xl font-bold text-[#101828]'>
								Turn Passion Into Profit
							</h4>
							<p className='text-[#667085]'>
								Your video library deserves more than storage. It deserves
								strategy, protection, and monetization support.
							</p>
							<div className='space-y-2'>
								{[
									'Safeguard content from unauthorized use',
									'Earn passive income while retaining ownership',
									'Unlock rights-cleared library access',
									'Platform support and monetization protection',
								].map((item) => (
									<div key={item} className='flex items-center gap-2 text-sm'>
										<Check className='h-4 w-4 text-[#16a34a]' />
										<span>{item}</span>
									</div>
								))}
							</div>
							<Button asChild className='rounded-full px-6'>
								<Link href='/sign-up'>For Creators</Link>
							</Button>
						</div>
					</div>
				</div>

				<div className='grid gap-6 lg:grid-cols-2 lg:items-start'>
					<div className='rounded-2xl border overflow-hidden bg-white min-h-[220px]'>
						<img
							src='https://bviral.com/wp-content/uploads/2025/05/homecreators.webp'
							alt='We know creators'
							className='h-full w-full object-cover'
							loading='lazy'
						/>
						<div className='p-4 border-t bg-gradient-to-r from-[#eff6ff] to-[#f5f3ff]'>
							<h4 className='text-2xl font-bold text-[#101828]'>We know creators...</h4>
							<p className='text-sm text-[#475467] mt-2'>
								We started as video owners too. We know how hard it is to
								protect and grow what you create.
							</p>
						</div>
					</div>

					<div className='rounded-2xl border bg-white p-5'>
						<h4 className='text-3xl font-bold text-[#101828] mb-3'>
							Unlock Your Potential...
						</h4>
						<Accordion type='single' collapsible defaultValue='item-1'>
							{serviceItems.map((service, index) => (
								<AccordionItem key={service} value={`item-${index + 1}`}>
									<AccordionTrigger className='text-left text-sm'>
										{service}
									</AccordionTrigger>
									<AccordionContent className='text-[#667085]'>
										BVIRAL provides end-to-end workflows for {service.toLowerCase()}
										, helping you scale quickly and safely.
									</AccordionContent>
								</AccordionItem>
							))}
						</Accordion>
					</div>
				</div>

				<div className='grid gap-6 lg:grid-cols-[0.7fr_1.3fr] lg:items-start border-t pt-8'>
					<div>
						<p className='text-xs uppercase tracking-[0.15em] text-[#667085] mb-3'>
							FAQ’s
						</p>
						<h4 className='text-3xl font-bold text-[#101828]'>
							Frequently Asked Questions
						</h4>
					</div>
					<Accordion type='single' collapsible className='bg-white rounded-2xl border px-4'>
						<AccordionItem value='faq-1'>
							<AccordionTrigger>Who is BVIRAL?</AccordionTrigger>
							<AccordionContent>
								BVIRAL is a licensing and distribution partner for creators,
								video owners, and brands.
							</AccordionContent>
						</AccordionItem>
						<AccordionItem value='faq-2'>
							<AccordionTrigger>
								What are the advantages of licensing a video with BVIRAL?
							</AccordionTrigger>
							<AccordionContent>
								You gain rights-cleared usage, monetization pathways, and broader
								distribution opportunities.
							</AccordionContent>
						</AccordionItem>
						<AccordionItem value='faq-3'>
							<AccordionTrigger>
								Why do established creators partner with BVIRAL?
							</AccordionTrigger>
							<AccordionContent>
								Because it combines content protection, expanded visibility, and
								a managed path to recurring revenue.
							</AccordionContent>
						</AccordionItem>
					</Accordion>
				</div>

				<div className='flex justify-center'>
					<Button asChild size='lg' className='rounded-full px-8'>
						<Link href='/sign-up'>
							Start with BVIRAL
							<Sparkles className='ml-2 h-4 w-4' />
						</Link>
					</Button>
				</div>
			</div>
		</section>
	);
}
