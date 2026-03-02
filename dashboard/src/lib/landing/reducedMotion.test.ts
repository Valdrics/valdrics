import { describe, expect, it, vi } from 'vitest';
import { getReducedMotionPreference, observeReducedMotionPreference } from './reducedMotion';

describe('reducedMotion helpers', () => {
	it('returns false when window or matchMedia is unavailable', () => {
		expect(getReducedMotionPreference(undefined)).toBe(false);
		expect(getReducedMotionPreference({} as Window)).toBe(false);
	});

	it('reads reduced-motion preference from matchMedia', () => {
		const matchMedia = vi.fn().mockReturnValue({ matches: true });
		expect(getReducedMotionPreference({ matchMedia } as unknown as Window)).toBe(true);
	});

	it('subscribes and unsubscribes using modern media query listeners', () => {
		const addEventListener = vi.fn();
		const removeEventListener = vi.fn();
		const win = {
			matchMedia: vi.fn().mockReturnValue({
				matches: false,
				addEventListener,
				removeEventListener
			})
		} as unknown as Window;
		const onChange = vi.fn();

		const stop = observeReducedMotionPreference(win, onChange);
		expect(onChange).toHaveBeenCalledWith(false);
		expect(addEventListener).toHaveBeenCalledTimes(1);

		stop();
		expect(removeEventListener).toHaveBeenCalledTimes(1);
	});
});
