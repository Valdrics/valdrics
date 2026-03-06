export interface LandingHeroLifecycleOptions {
	documentRef: Document;
	windowRef: Window;
	signalMapElement: HTMLDivElement | null;
	scrollMilestones: readonly number[];
	onDocumentVisibilityChange: (isVisible: boolean) => void;
	onSignalMapVisibilityChange: (isVisible: boolean) => void;
	onSectionView: (sectionId: string) => void;
	onScrollProgressChange: (progressPct: number) => void;
	onScrollMilestone: (milestone: number) => void;
}

export function setupLandingHeroLifecycle(options: LandingHeroLifecycleOptions): () => void {
	const {
		documentRef,
		windowRef,
		signalMapElement,
		scrollMilestones,
		onDocumentVisibilityChange,
		onSignalMapVisibilityChange,
		onSectionView,
		onScrollProgressChange,
		onScrollMilestone
	} = options;

	onDocumentVisibilityChange(documentRef.visibilityState === 'visible');
	const handleVisibility = () => {
		onDocumentVisibilityChange(documentRef.visibilityState === 'visible');
	};
	documentRef.addEventListener('visibilitychange', handleVisibility);

	let signalMapObserver: IntersectionObserver | null = null;
	if (signalMapElement && typeof IntersectionObserver !== 'undefined') {
		signalMapObserver = new IntersectionObserver(
			(entries) => {
				const entry = entries[0];
				onSignalMapVisibilityChange(
					Boolean(entry?.isIntersecting && entry.intersectionRatio > 0.12)
				);
			},
			{ threshold: [0, 0.12, 0.5] }
		);
		signalMapObserver.observe(signalMapElement);
	}

	const seenSections = new Set<string>();
	let sectionObserver: IntersectionObserver | null = null;
	const landingSections = Array.from(
		documentRef.querySelectorAll<HTMLElement>('[data-landing-section]')
	);
	if (landingSections.length > 0 && typeof IntersectionObserver !== 'undefined') {
		sectionObserver = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					if (!entry.isIntersecting || entry.intersectionRatio < 0.35) {
						continue;
					}
					const sectionId = (entry.target as HTMLElement).dataset.landingSection?.trim();
					if (!sectionId || seenSections.has(sectionId)) {
						continue;
					}
					seenSections.add(sectionId);
					onSectionView(sectionId);
				}
			},
			{ threshold: [0.15, 0.35, 0.6] }
		);

		for (const section of landingSections) {
			sectionObserver.observe(section);
		}
	}

	const seenMilestones = new Set<number>();
	const handleScroll = () => {
		const root = documentRef.documentElement;
		const maxScrollable = Math.max(1, root.scrollHeight - windowRef.innerHeight);
		const scrollProgress = Math.min(100, Math.max(0, (windowRef.scrollY / maxScrollable) * 100));
		onScrollProgressChange(scrollProgress);
		for (const milestone of scrollMilestones) {
			if (scrollProgress < milestone || seenMilestones.has(milestone)) {
				continue;
			}
			seenMilestones.add(milestone);
			onScrollMilestone(milestone);
		}
	};

	windowRef.addEventListener('scroll', handleScroll, { passive: true });
	handleScroll();

	return () => {
		documentRef.removeEventListener('visibilitychange', handleVisibility);
		windowRef.removeEventListener('scroll', handleScroll);
		signalMapObserver?.disconnect();
		sectionObserver?.disconnect();
	};
}
