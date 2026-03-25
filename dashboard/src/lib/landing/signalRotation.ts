export function nextSnapshotIndex(currentIndex: number, totalSnapshots: number): number {
	if (!Number.isFinite(totalSnapshots) || totalSnapshots <= 0) {
		return 0;
	}
	if (!Number.isFinite(currentIndex)) {
		return 0;
	}

	const normalizedTotal = Math.floor(totalSnapshots);
	const normalizedCurrent = Math.trunc(currentIndex);
	const safeCurrent = ((normalizedCurrent % normalizedTotal) + normalizedTotal) % normalizedTotal;
	return (safeCurrent + 1) % normalizedTotal;
}
