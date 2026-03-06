export type ScimGroupMapping = {
	group: string;
	role: 'admin' | 'member';
	persona: 'engineering' | 'finance' | 'platform' | 'leadership' | null;
};

export type IdentitySettings = {
	sso_enabled: boolean;
	allowed_email_domains: string[];
	sso_federation_enabled: boolean;
	sso_federation_mode: 'domain' | 'provider_id';
	sso_federation_provider_id: string;
	scim_enabled: boolean;
	has_scim_token: boolean;
	scim_last_rotated_at: string | null;
	scim_group_mappings: ScimGroupMapping[];
};

export type IdentityDiagnostics = {
	tier: string;
	sso: {
		enabled: boolean;
		allowed_email_domains: string[];
		enforcement_active: boolean;
		federation_enabled: boolean;
		federation_mode: 'domain' | 'provider_id';
		federation_ready: boolean;
		current_admin_domain: string | null;
		current_admin_domain_allowed: boolean | null;
		issues: string[];
	};
	scim: {
		available: boolean;
		enabled: boolean;
		has_token: boolean;
		token_blind_index_present: boolean;
		last_rotated_at: string | null;
		token_age_days: number | null;
		rotation_recommended_days: number;
		rotation_overdue: boolean;
		issues: string[];
	};
	recommendations: string[];
};
