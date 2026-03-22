export type PublicTheme = 'light' | 'dark';

export const PUBLIC_THEME_STORAGE_KEY = 'valdrics.public.theme.v1';

type StorageLike = Pick<Storage, 'getItem' | 'setItem'>;
type MatchMediaFn = (query: string) => Pick<MediaQueryList, 'matches'>;

export function isPublicTheme(value: string | null | undefined): value is PublicTheme {
	return value === 'light' || value === 'dark';
}

export function readStoredPublicTheme(storage: StorageLike | null | undefined): PublicTheme | null {
	if (!storage) return null;
	const storedValue = storage.getItem(PUBLIC_THEME_STORAGE_KEY);
	return isPublicTheme(storedValue) ? storedValue : null;
}

export function resolveInitialPublicTheme(options: {
	storage?: StorageLike | null;
	matchMedia?: MatchMediaFn | null;
}): PublicTheme {
	const storedValue = readStoredPublicTheme(options.storage);
	if (storedValue) return storedValue;
	if (options.matchMedia?.('(prefers-color-scheme: dark)').matches) {
		return 'dark';
	}
	return 'light';
}

export function persistPublicTheme(
	storage: StorageLike | null | undefined,
	theme: PublicTheme
): void {
	storage?.setItem(PUBLIC_THEME_STORAGE_KEY, theme);
}

export function togglePublicTheme(theme: PublicTheme): PublicTheme {
	return theme === 'dark' ? 'light' : 'dark';
}
