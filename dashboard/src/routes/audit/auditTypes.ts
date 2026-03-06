export type AuditLog = {
	id: string;
	event_type: string;
	event_timestamp: string;
	actor_email?: string | null;
	resource_type?: string | null;
	resource_id?: string | null;
	success: boolean;
	correlation_id?: string | null;
};

export type AuditDetail = {
	id: string;
	event_type: string;
	event_timestamp: string;
	actor_email?: string | null;
	actor_ip?: string | null;
	request_method?: string | null;
	request_path?: string | null;
	resource_type?: string | null;
	resource_id?: string | null;
	success: boolean;
	error_message?: string | null;
	details?: Record<string, unknown> | null;
};
