import {
	runDiscoveryStageAFlow,
	runDiscoveryStageBFlow,
	updateDiscoveryCandidateStatusFlow
} from './onboardingFlowActions';
import type { DiscoveryCandidate, IdpProvider } from './onboardingTypesUtils';

type DiscoveryFlowResult = {
	info?: string;
	domain: string;
	warnings: string[];
	candidates: DiscoveryCandidate[];
};

type ApplyDiscoveryFlowResult = (result: DiscoveryFlowResult) => void;
type SetMessage = (value: string) => void;
type SetLoading = (value: boolean) => void;
type SetActionCandidateId = (value: string | null) => void;
type UpdateDiscoveryAction = 'accept' | 'ignore' | 'connected';

type TokenProvider = () => Promise<string | null>;
type EnsureOnboarded = () => Promise<boolean>;

export async function runOnboardingDiscoveryStageA(args: {
	discoveryEmail: string;
	getAccessToken: TokenProvider;
	ensureOnboarded: EnsureOnboarded;
	setError: SetMessage;
	setInfo: SetMessage;
	setLoading: SetLoading;
	applyDiscoveryFlowResult: ApplyDiscoveryFlowResult;
}): Promise<void> {
	args.setError('');
	args.setInfo('');
	args.setLoading(true);
	try {
		args.applyDiscoveryFlowResult(
			await runDiscoveryStageAFlow({
				email: args.discoveryEmail,
				getAccessToken: args.getAccessToken,
				ensureOnboarded: args.ensureOnboarded
			})
		);
	} catch (error) {
		const err = error as Error;
		args.setError(err.message || 'Failed to run Stage A discovery');
	} finally {
		args.setLoading(false);
	}
}

export async function runOnboardingDiscoveryStageB(args: {
	discoveryDomain: string;
	discoveryEmail: string;
	discoveryIdpProvider: IdpProvider;
	canUseIdpDeepScan: boolean;
	getAccessToken: TokenProvider;
	ensureOnboarded: EnsureOnboarded;
	setError: SetMessage;
	setInfo: SetMessage;
	setLoading: SetLoading;
	applyDiscoveryFlowResult: ApplyDiscoveryFlowResult;
}): Promise<void> {
	args.setError('');
	args.setInfo('');
	args.setLoading(true);
	try {
		args.applyDiscoveryFlowResult(
			await runDiscoveryStageBFlow({
				discoveryDomain: args.discoveryDomain,
				discoveryEmail: args.discoveryEmail,
				idpProvider: args.discoveryIdpProvider,
				canUseIdpDeepScan: args.canUseIdpDeepScan,
				getAccessToken: args.getAccessToken,
				ensureOnboarded: args.ensureOnboarded
			})
		);
	} catch (error) {
		const err = error as Error;
		args.setError(err.message || 'Failed to run Stage B deep scan');
	} finally {
		args.setLoading(false);
	}
}

export async function updateOnboardingDiscoveryCandidateStatus(args: {
	candidate: DiscoveryCandidate;
	action: UpdateDiscoveryAction;
	getAccessToken: TokenProvider;
	applyDiscoveryCandidateLocally: (updated: DiscoveryCandidate) => void;
	setError: SetMessage;
	setInfo: SetMessage;
	setActionCandidateId: SetActionCandidateId;
}): Promise<DiscoveryCandidate | null> {
	args.setError('');
	args.setInfo('');
	args.setActionCandidateId(args.candidate.id);
	try {
		const payload = await updateDiscoveryCandidateStatusFlow({
			getAccessToken: args.getAccessToken,
			candidateId: args.candidate.id,
			action: args.action
		});
		args.applyDiscoveryCandidateLocally(payload);
		return payload;
	} catch (error) {
		const err = error as Error;
		args.setError(err.message || `Failed to ${args.action} discovery candidate`);
		return null;
	} finally {
		args.setActionCandidateId(null);
	}
}
