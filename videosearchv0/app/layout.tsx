import type React from 'react';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { ThemeProvider } from '@/components/theme-provider';
import { Header } from '@/components/header';
import { Footer } from '@/components/footer';
import { HelpAssistantChatbot } from '@/components/help-assistant-chatbot';
import { ClerkProvider, SignedIn } from '@clerk/nextjs';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';
import { CategoriesProvider } from './context/CategoriesContext';

const geistSans = Geist({
	variable: '--font-geist-sans',
	subsets: ['latin'],
});

const geistMono = Geist_Mono({
	variable: '--font-geist-mono',
	subsets: ['latin'],
});

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
	title: 'BVIRAL - Premium Video Library',
	description:
		'Discover, license, and download high-quality videos for your projects',
	generator: 'v0.dev',
};

export default function RootLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	return (
		<ClerkProvider>
			<html lang='en' suppressHydrationWarning>
				<body
					className={`${inter.className} ${geistSans.variable} ${geistMono.variable} antialiased`}
				>
					<ThemeProvider
						attribute='class'
						defaultTheme='light'
						enableSystem={false}
						disableTransitionOnChange
					>
						<CategoriesProvider>
							{' '}
							{/* <- wrap here */}
								<div className='min-h-screen flex flex-col'>
									<Header />
									<main className='flex-1'>{children}</main>
									<Footer />
									<SignedIn>
										<HelpAssistantChatbot />
									</SignedIn>
								</div>
						</CategoriesProvider>
					</ThemeProvider>
				</body>
			</html>
		</ClerkProvider>
	);
}
