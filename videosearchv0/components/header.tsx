'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Menu } from 'lucide-react';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { UserButton, useAuth } from '@clerk/nextjs';
import { buildSigninPortalUrl } from '@/lib/auth-portal';

export function Header() {
	const { isLoaded, isSignedIn } = useAuth();

	return (
		<header className='sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60'>
			<div className='container mx-auto px-4 h-16 flex items-center justify-between'>
				{/* Logo */}
				<Link href='/' className='flex items-center space-x-2'>
					<div className='w-24 h-4 bg-primary flex items-center justify-center'>
						<img src='/bviral.png' alt='BViral' />
					</div>
				</Link>

				{/* Desktop Navigation */}
					<nav className='hidden md:flex items-center space-x-8'>
						<Link
							href='/'
							className='text-sm font-medium hover:text-primary transition-colors'
						>
							Home
						</Link>
						<Link
							href='/search'
							className='text-sm font-medium hover:text-primary transition-colors'
						>
							Browse
						</Link>
						<Link
							href='/categories'
							className='text-sm font-medium hover:text-primary transition-colors'
						>
							Categories
						</Link>
					</nav>

				{/* User Actions */}
				<div className='flex items-center space-x-4'>
					{isLoaded && isSignedIn ? (
						<UserButton />
					) : (
						<Button asChild size='sm'>
							<Link href={buildSigninPortalUrl()}>Login</Link>
						</Button>
					)}

					{/* Mobile Menu */}
					<Sheet>
						<SheetTrigger asChild>
							<Button variant='ghost' size='sm' className='md:hidden'>
								<Menu className='h-4 w-4' />
							</Button>
						</SheetTrigger>
						<SheetContent side='right'>
							<nav className='flex flex-col space-y-4 mt-8'>
								<Link href='/' className='text-sm font-medium'>
									Home
								</Link>
								<Link href='/search' className='text-sm font-medium'>
									Browse
								</Link>
								<Link href='/categories' className='text-sm font-medium'>
									Categories
								</Link>
								<Link
									href={buildSigninPortalUrl()}
									className='text-sm font-medium'
								>
									Login
								</Link>
							</nav>
						</SheetContent>
					</Sheet>
				</div>
			</div>
		</header>
	);
}
