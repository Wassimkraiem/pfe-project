const SIGNUP_PORTAL_BASE_URL =
	process.env.NEXT_PUBLIC_SIGNUP_PORTAL_URL?.replace(/\/$/, '') ||
	'http://localhost:3002';

function buildAuthPortalUrl(
	pathname: string,
	returnUrl?: string,
	returnKey: 'redirect_url' | 'return_url' = 'redirect_url'
) {
	const url = new URL(pathname, SIGNUP_PORTAL_BASE_URL);
	if (returnUrl) {
		url.searchParams.set(returnKey, returnUrl);
	}
	return url.toString();
}

export function buildSignupPortalUrl(returnUrl?: string) {
	return buildAuthPortalUrl('/signup', returnUrl, 'redirect_url');
}

export function buildSigninPortalUrl(returnUrl?: string) {
	return buildAuthPortalUrl('/signin', returnUrl, 'return_url');
}

export function buildDashboardPortalUrl() {
	return buildAuthPortalUrl('/dashboard');
}

export function redirectToSignupPortal() {
	if (typeof window === 'undefined') {
		return;
	}
	window.location.href = buildSignupPortalUrl(window.location.href);
}

export function redirectToSigninPortal() {
	if (typeof window === 'undefined') {
		return;
	}
	window.location.href = buildSigninPortalUrl(window.location.href);
}
