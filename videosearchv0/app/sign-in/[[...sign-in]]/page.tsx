import { redirect } from 'next/navigation';
import { buildSigninPortalUrl } from '@/lib/auth-portal';

export default async function Page({
	searchParams,
}: {
	searchParams: Promise<{ redirect_url?: string; return_url?: string }>;
}) {
	const params = await searchParams;
	const returnUrl = params.return_url || params.redirect_url;
	redirect(buildSigninPortalUrl(returnUrl));
}
