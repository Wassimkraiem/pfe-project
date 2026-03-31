import { redirect } from 'next/navigation';
import { buildSignupPortalUrl } from '@/lib/auth-portal';

export default async function Page({
	searchParams,
}: {
	searchParams: Promise<{ redirect_url?: string }>;
}) {
	const params = await searchParams;
	redirect(buildSignupPortalUrl(params.redirect_url));
}
