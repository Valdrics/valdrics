export function getReducedMotionPreference(win: Window | undefined): boolean {
	if (!win || typeof win.matchMedia !== 'function') {
		return false;
	}
	return win.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function observeReducedMotionPreference(
	win: Window | undefined,
	onChange: (value: boolean) => void
): () => void {
	if (!win || typeof win.matchMedia !== 'function') {
		onChange(false);
		return () => {};
	}

	const media = win.matchMedia('(prefers-reduced-motion: reduce)');
	const handleChange = () => onChange(Boolean(media.matches));

	handleChange();
	if (typeof media.addEventListener === 'function') {
		media.addEventListener('change', handleChange);
		return () => media.removeEventListener('change', handleChange);
	}
	if (typeof media.addListener === 'function') {
		media.addListener(handleChange);
		return () => media.removeListener(handleChange);
	}
	return () => {};
}
