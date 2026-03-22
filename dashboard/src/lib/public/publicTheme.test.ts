import { describe, expect, it, vi } from 'vitest';
import {
	PUBLIC_THEME_STORAGE_KEY,
	persistPublicTheme,
	readStoredPublicTheme,
	resolveInitialPublicTheme,
	togglePublicTheme
} from './publicTheme';

describe('publicTheme', () => {
	it('defaults to light when there is no stored or system preference', () => {
		expect(
			resolveInitialPublicTheme({
				storage: {
					getItem: vi.fn().mockReturnValue(null),
					setItem: vi.fn()
				},
				matchMedia: vi.fn().mockReturnValue({ matches: false })
			})
		).toBe('light');
	});

	it('uses the stored preference when available', () => {
		expect(
			resolveInitialPublicTheme({
				storage: {
					getItem: vi.fn().mockReturnValue('dark'),
					setItem: vi.fn()
				},
				matchMedia: vi.fn().mockReturnValue({ matches: false })
			})
		).toBe('dark');
	});

	it('falls back to system dark mode when no stored preference exists', () => {
		expect(
			resolveInitialPublicTheme({
				storage: {
					getItem: vi.fn().mockReturnValue(null),
					setItem: vi.fn()
				},
				matchMedia: vi.fn().mockReturnValue({ matches: true })
			})
		).toBe('dark');
	});

	it('ignores invalid stored values', () => {
		expect(
			readStoredPublicTheme({
				getItem: vi.fn().mockReturnValue('sepia'),
				setItem: vi.fn()
			})
		).toBeNull();
	});

	it('persists and toggles the theme value', () => {
		const setItem = vi.fn();
		persistPublicTheme(
			{
				getItem: vi.fn(),
				setItem
			},
			'dark'
		);
		expect(setItem).toHaveBeenCalledWith(PUBLIC_THEME_STORAGE_KEY, 'dark');
		expect(togglePublicTheme('dark')).toBe('light');
		expect(togglePublicTheme('light')).toBe('dark');
	});
});
