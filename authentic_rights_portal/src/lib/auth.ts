export type GetTokenFn = (opts?: { template?: string }) => Promise<string | null>;

const JWT_TEMPLATE =
  typeof process !== "undefined"
    ? process.env.NEXT_PUBLIC_CLERK_JWT_TEMPLATE?.trim()
    : undefined;

export async function getApiToken(getToken: GetTokenFn): Promise<string | null> {
  if (JWT_TEMPLATE) {
    return getToken({ template: JWT_TEMPLATE });
  }
  return getToken();
}
