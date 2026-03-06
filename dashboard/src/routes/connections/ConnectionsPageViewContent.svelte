<script lang="ts">
	/* eslint-disable svelte/no-navigation-without-resolve */
	import { onMount } from 'svelte';
	import {
		buildCloudPlusCreateFields,
		createAndVerifyCloudPlusConnection,
		resetCloudPlusForms,
		verifyCloudPlusConnectionRequest,
		type CloudPlusProvider,
		type ConnectionsCloudPlusFormsState
	} from './connectionsCloudPlusActions';
	import {
		deleteConnectionApi,
		linkAwsDiscoveredAccount,
		loadAwsDiscoveredAccounts,
		loadConnectionsSnapshot,
		type CloudConnection,
		type DiscoveredAccount,
		syncAwsOrg as syncAwsOrgApi
	} from './connectionsDataApi';
	import ConnectionsPageViewBody from './ConnectionsPageViewBody.svelte';
	import './ConnectionsPageViewContent.css';

	let { data } = $props();
	let loadingAWS = $state(true), loadingAzure = $state(true), loadingGCP = $state(true);
	let loadingSaaS = $state(true), loadingLicense = $state(true), loadingPlatform = $state(true), loadingHybrid = $state(true);
	let awsConnection = $state<CloudConnection | null>(null);
	let awsConnections = $state<CloudConnection[]>([]), azureConnections = $state<CloudConnection[]>([]), gcpConnections = $state<CloudConnection[]>([]);
	let saasConnections = $state<CloudConnection[]>([]), licenseConnections = $state<CloudConnection[]>([]), platformConnections = $state<CloudConnection[]>([]), hybridConnections = $state<CloudConnection[]>([]);
	let discoveredAccounts = $state<DiscoveredAccount[]>([]);
	let loadingDiscovered = $state(false);
	let syncingOrg = $state(false);
	let linkingAccount: string | null = $state(null);

	let error = $state('');
	let success = $state('');
	const CONNECTION_REQUEST_TIMEOUT_MS = 8000;

	const cloudPlusTierAllowed = ['pro', 'enterprise'];
	let verifyingCloudPlus = $state<Record<string, boolean>>({});
	let creatingSaaS = $state(false), creatingLicense = $state(false), creatingPlatform = $state(false), creatingHybrid = $state(false);
	let saasName = $state(''), saasVendor = $state('stripe');
	let saasAuthMethod = $state<'manual' | 'api_key' | 'oauth' | 'csv'>('api_key');
	let saasApiKey = $state(''), saasConnectorConfig = $state('{}'), saasFeedInput = $state('[]');
	let licenseName = $state(''), licenseVendor = $state('microsoft_365');
	let licenseAuthMethod = $state<'manual' | 'api_key' | 'oauth' | 'csv'>('oauth');
	let licenseApiKey = $state(''), licenseConnectorConfig = $state('{"default_seat_price_usd": 36}'), licenseFeedInput = $state('[]');
	let platformName = $state(''), platformVendor = $state('internal_platform');
	let platformAuthMethod = $state<'manual' | 'csv' | 'api_key'>('manual');
	let platformApiKey = $state(''), platformApiSecret = $state(''), platformConnectorConfig = $state('{}'), platformFeedInput = $state('[]');
	let hybridName = $state(''), hybridVendor = $state('datacenter');
	let hybridAuthMethod = $state<'manual' | 'csv' | 'api_key'>('manual');
	let hybridApiKey = $state(''), hybridApiSecret = $state(''), hybridConnectorConfig = $state('{}'), hybridFeedInput = $state('[]');

	const canUseCloudPlusFeatures = (): boolean => cloudPlusTierAllowed.includes(data.subscription?.tier);

	function isCreatingCloudPlus(provider: CloudPlusProvider): boolean {
		if (provider === 'saas') return creatingSaaS;
		if (provider === 'license') return creatingLicense;
		if (provider === 'platform') return creatingPlatform;
		return creatingHybrid;
	}

	function setCreatingCloudPlus(provider: CloudPlusProvider, value: boolean): void {
		if (provider === 'saas') creatingSaaS = value;
		else if (provider === 'license') creatingLicense = value;
		else if (provider === 'platform') creatingPlatform = value;
		else creatingHybrid = value;
	}

	function getCloudPlusFormsState(): ConnectionsCloudPlusFormsState {
		return {
			saasName,
			saasVendor,
			saasAuthMethod,
			saasApiKey,
			saasConnectorConfig,
			saasFeedInput,
			licenseName,
			licenseVendor,
			licenseAuthMethod,
			licenseApiKey,
			licenseConnectorConfig,
			licenseFeedInput,
			platformName,
			platformVendor,
			platformAuthMethod,
			platformApiKey,
			platformApiSecret,
			platformConnectorConfig,
			platformFeedInput,
			hybridName,
			hybridVendor,
			hybridAuthMethod,
			hybridApiKey,
			hybridApiSecret,
			hybridConnectorConfig,
			hybridFeedInput
		};
	}

	function applyCloudPlusFormsState(next: ConnectionsCloudPlusFormsState): void {
		saasName = next.saasName;
		saasVendor = next.saasVendor;
		saasAuthMethod = next.saasAuthMethod;
		saasApiKey = next.saasApiKey;
		saasConnectorConfig = next.saasConnectorConfig;
		saasFeedInput = next.saasFeedInput;
		licenseName = next.licenseName;
		licenseVendor = next.licenseVendor;
		licenseAuthMethod = next.licenseAuthMethod;
		licenseApiKey = next.licenseApiKey;
		licenseConnectorConfig = next.licenseConnectorConfig;
		licenseFeedInput = next.licenseFeedInput;
		platformName = next.platformName;
		platformVendor = next.platformVendor;
		platformAuthMethod = next.platformAuthMethod;
		platformApiKey = next.platformApiKey;
		platformApiSecret = next.platformApiSecret;
		platformConnectorConfig = next.platformConnectorConfig;
		platformFeedInput = next.platformFeedInput;
		hybridName = next.hybridName;
		hybridVendor = next.hybridVendor;
		hybridAuthMethod = next.hybridAuthMethod;
		hybridApiKey = next.hybridApiKey;
		hybridApiSecret = next.hybridApiSecret;
		hybridConnectorConfig = next.hybridConnectorConfig;
		hybridFeedInput = next.hybridFeedInput;
	}

	async function createCloudPlusConnection(provider: CloudPlusProvider) {
		if (!canUseCloudPlusFeatures()) {
			error = 'Cloud+ connectors require Pro tier or higher.';
			return;
		}

		if (isCreatingCloudPlus(provider)) return;
		setCreatingCloudPlus(provider, true);

		success = '';
		error = '';
		try {
			const fields = buildCloudPlusCreateFields(provider, getCloudPlusFormsState());
			const created = await createAndVerifyCloudPlusConnection({
				provider,
				accessToken: data.session?.access_token,
				fields
			});
			success = created.message;
			await loadConnections();
			applyCloudPlusFormsState(resetCloudPlusForms(provider, getCloudPlusFormsState()));
		} catch (e) {
			const err = e as Error;
			error = err.message;
		} finally {
			setCreatingCloudPlus(provider, false);
		}
	}

	async function verifyCloudPlusConnection(provider: CloudPlusProvider, connectionId: string) {
		verifyingCloudPlus = { ...verifyingCloudPlus, [connectionId]: true };
		success = '';
		error = '';
		try {
			const verified = await verifyCloudPlusConnectionRequest({
				provider,
				connectionId,
				accessToken: data.session?.access_token
			});
			success = verified.message;
			await loadConnections();
		} catch (e) {
			const err = e as Error;
			error = err.message;
		} finally {
			verifyingCloudPlus = { ...verifyingCloudPlus, [connectionId]: false };
		}
	}

	async function loadConnections() {
		loadingAWS = true;
		loadingAzure = true;
		loadingGCP = true;
		loadingSaaS = true;
		loadingLicense = true;
		loadingPlatform = true;
		loadingHybrid = true;
		error = '';

		try {
			const snapshot = await loadConnectionsSnapshot(
				data.session?.access_token,
				CONNECTION_REQUEST_TIMEOUT_MS
			);
			awsConnections = snapshot.aws;
			awsConnection = awsConnections.length > 0 ? awsConnections[0] : null;
			azureConnections = snapshot.azure;
			gcpConnections = snapshot.gcp;
			saasConnections = snapshot.saas;
			licenseConnections = snapshot.license;
			platformConnections = snapshot.platform;
			hybridConnections = snapshot.hybrid;

			if (snapshot.timedOutCount > 0) {
				error = `${snapshot.timedOutCount} connection sections timed out. You can retry or refresh the page.`;
			}

			if (awsConnection?.is_management_account) {
				void loadDiscoveredAccounts();
			}
		} catch (e) {
			const err = e as Error;
			error = err.message || 'Failed to load cloud accounts. Check backend connection.';
			awsConnections = [];
			awsConnection = null;
			azureConnections = [];
			gcpConnections = [];
			saasConnections = [];
			licenseConnections = [];
			platformConnections = [];
			hybridConnections = [];
		} finally {
			loadingAWS = false;
			loadingAzure = false;
			loadingGCP = false;
			loadingSaaS = false;
			loadingLicense = false;
			loadingPlatform = false;
			loadingHybrid = false;
		}
	}

	async function loadDiscoveredAccounts() {
		loadingDiscovered = true;
		try {
			discoveredAccounts = await loadAwsDiscoveredAccounts(
				data.session?.access_token,
				CONNECTION_REQUEST_TIMEOUT_MS
			);
		} catch {
			discoveredAccounts = [];
		} finally {
			loadingDiscovered = false;
		}
	}

	async function syncAWSOrg() {
		if (!awsConnection) return;
		syncingOrg = true;
		success = '';
		error = '';
		try {
			success = await syncAwsOrgApi(data.session?.access_token, awsConnection.id);
			await loadDiscoveredAccounts();
			setTimeout(() => (success = ''), 3000);
		} catch (e) {
			const err = e as Error;
			error = err.message;
		} finally {
			syncingOrg = false;
		}
	}

	async function deleteConnection(provider: string, id: string) {
		if (
			!confirm(
				`Are you sure you want to delete this ${provider.toUpperCase()} connection? Data fetching will stop immediately.`
			)
		) {
			return;
		}

		success = '';
		error = '';
		try {
			const result = await deleteConnectionApi(data.session?.access_token, provider, id);
			if (result.status === 204 || result.status === 404) {
				success = `${provider.toUpperCase()} connection deleted successfully.`;

				if (provider === 'aws' && awsConnection?.id === id) {
					discoveredAccounts = [];
					awsConnection = null;
				}

				await loadConnections();
				setTimeout(() => (success = ''), 3000);
			} else {
				throw new Error(result.detail || 'Delete failed');
			}
		} catch (e) {
			const err = e as Error;
			error = err.message;
		}
	}

	async function linkDiscoveredAccount(discoveredId: string) {
		linkingAccount = discoveredId;
		success = '';
		error = '';
		try {
			success = await linkAwsDiscoveredAccount(data.session?.access_token, discoveredId);
			await loadDiscoveredAccounts();
			await loadConnections();
			setTimeout(() => (success = ''), 3000);
		} catch (e) {
			const err = e as Error;
			error = err.message;
		} finally {
			linkingAccount = null;
		}
	}

	onMount(() => {
		if (!data.user || !data.session?.access_token) {
			loadingAWS = false;
			loadingAzure = false;
			loadingGCP = false;
			loadingSaaS = false;
			loadingLicense = false;
			loadingPlatform = false;
			loadingHybrid = false;
			return;
		}
		void loadConnections();
	});
</script>

<svelte:head>
	<title>Cloud Accounts | Valdrics</title>
</svelte:head>

<div class="space-y-8">
	<ConnectionsPageViewBody
		{...{
			data,
			loadingAWS,
			loadingAzure,
			loadingGCP,
			loadingSaaS,
			loadingLicense,
			loadingPlatform,
			loadingHybrid,
			awsConnection,
			awsConnections,
			azureConnections,
			gcpConnections,
			saasConnections,
			licenseConnections,
			platformConnections,
			hybridConnections,
			discoveredAccounts,
			loadingDiscovered,
			syncingOrg,
			linkingAccount,
			error,
			success,
			verifyingCloudPlus,
			creatingSaaS,
			creatingLicense,
			creatingPlatform,
			creatingHybrid,
			canUseCloudPlusFeatures,
			createCloudPlusConnection,
			verifyCloudPlusConnection,
			syncAWSOrg,
			deleteConnection,
			linkDiscoveredAccount
		}}
		bind:saasName
		bind:saasVendor
		bind:saasAuthMethod
		bind:saasApiKey
		bind:saasConnectorConfig
		bind:saasFeedInput
		bind:licenseName
		bind:licenseVendor
		bind:licenseAuthMethod
		bind:licenseApiKey
		bind:licenseConnectorConfig
		bind:licenseFeedInput
		bind:platformName
		bind:platformVendor
		bind:platformAuthMethod
		bind:platformApiKey
		bind:platformApiSecret
		bind:platformConnectorConfig
		bind:platformFeedInput
		bind:hybridName
		bind:hybridVendor
		bind:hybridAuthMethod
		bind:hybridApiKey
		bind:hybridApiSecret
		bind:hybridConnectorConfig
		bind:hybridFeedInput
	/>
</div>
