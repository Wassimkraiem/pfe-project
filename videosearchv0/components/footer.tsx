import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export function Footer() {
	return (
		<footer className='bg-muted/50 border-t'>
			<div className='container mx-auto px-4 py-12'>
				<div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8'>
					{/* Brand */}
					<div className='space-y-4'>
						<Link href='/' className='flex items-center space-x-2'>
							<div className='w-24 h-4 bg-primary flex items-center justify-center'>
								<img src='/bviral.png'></img>
							</div>
						</Link>
						<p className='text-sm text-muted-foreground'>
							Your premier destination for high-quality video content. Discover,
							license, and download videos for all your creative projects.
						</p>
						<div className='flex space-x-2'>
							<Button variant='ghost' size='sm' aria-label='Facebook'>
								Fb
							</Button>
							<Button variant='ghost' size='sm' aria-label='Twitter'>
								X
							</Button>
							<Button variant='ghost' size='sm' aria-label='Instagram'>
								Ig
							</Button>
							<Button variant='ghost' size='sm' aria-label='YouTube'>
								YT
							</Button>
						</div>
					</div>

					{/* Quick Links */}
					<div className='space-y-4'>
						<h3 className='font-semibold'>Quick Links</h3>
						<nav className='flex flex-col space-y-2 text-sm'>
							<Link
								href='/search'
								className='text-muted-foreground hover:text-foreground transition-colors'
							>
								Browse Videos
							</Link>
							<Link
								href='/categories'
								className='text-muted-foreground hover:text-foreground transition-colors'
							>
								Categories
							</Link>
							<Link
								href='/pricing'
								className='text-muted-foreground hover:text-foreground transition-colors'
							>
								Pricing
							</Link>
							<Link
								href='/about'
								className='text-muted-foreground hover:text-foreground transition-colors'
							>
								About Us
							</Link>
						</nav>
					</div>

					{/* Support */}
					<div className='space-y-4'>
						<h3 className='font-semibold'>Support</h3>
						<nav className='flex flex-col space-y-2 text-sm'>
							<Link
								href='/help'
								className='text-muted-foreground hover:text-foreground transition-colors'
							>
								Help Center
							</Link>
							<Link
								href='/contact'
								className='text-muted-foreground hover:text-foreground transition-colors'
							>
								Contact Us
							</Link>
							<Link
								href='/licenses'
								className='text-muted-foreground hover:text-foreground transition-colors'
							>
								License Info
							</Link>
							<Link
								href='/faq'
								className='text-muted-foreground hover:text-foreground transition-colors'
							>
								FAQ
							</Link>
						</nav>
					</div>

					{/* Newsletter */}
					<div className='space-y-4'>
						<h3 className='font-semibold'>Stay Updated</h3>
						<p className='text-sm text-muted-foreground'>
							Subscribe to get notified about new videos and features.
						</p>
						<div className='flex space-x-2'>
							<Input
								type='email'
								placeholder='Enter your email'
								className='flex-1'
							/>
							<Button size='sm'>Subscribe</Button>
						</div>
					</div>
				</div>

				<div className='border-t mt-8 pt-8 flex flex-col md:flex-row justify-between items-center'>
					<p className='text-sm text-muted-foreground'>
						© {new Date().getFullYear()} BVIRAL. All rights reserved.
					</p>
					<nav className='flex space-x-6 text-sm text-muted-foreground mt-4 md:mt-0'>
						<Link
							href='/privacy'
							className='hover:text-foreground transition-colors'
						>
							Privacy Policy
						</Link>
						<Link
							href='/terms'
							className='hover:text-foreground transition-colors'
						>
							Terms of Service
						</Link>
						<Link
							href='/cookies'
							className='hover:text-foreground transition-colors'
						>
							Cookie Policy
						</Link>
					</nav>
				</div>
			</div>
		</footer>
	);
}
