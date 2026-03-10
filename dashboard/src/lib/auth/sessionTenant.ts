import type { Session, User } from '@supabase/supabase-js';

type SessionTenantInput = {
	session?: Session | null;
	user?: User | null;
};

export function resolveSessionTenantId(input: SessionTenantInput): string | undefined {
	const runtimeTenantId = (input.user as { tenant_id?: unknown } | null | undefined)?.tenant_id;
	if (typeof runtimeTenantId === 'string' && runtimeTenantId.trim().length > 0) {
		return runtimeTenantId;
	}

	const metadataTenantId = input.session?.user?.user_metadata?.tenant_id;
	if (typeof metadataTenantId === 'string' && metadataTenantId.trim().length > 0) {
		return metadataTenantId;
	}

	return undefined;
}
