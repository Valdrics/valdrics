"""Scheduler remediation sweep orchestration helpers."""

from __future__ import annotations

from typing import Any, Callable


async def remediation_sweep_logic(
    *,
    open_db_session_fn: Callable[[], Any],
    scheduler_span_fn: Callable[..., Any],
    system_sweep_connection_limit_fn: Callable[[], int],
    cap_scope_items_fn: Callable[..., list[Any]],
    logger: Any,
    list_active_connections_all_tenants_fn: Callable[..., Any],
    is_connection_active_fn: Callable[[Any], bool],
    scheduler_orchestrator_cls: Any,
    async_session_maker_fn: Any,
    resolve_provider_from_connection_fn: Callable[[Any], Any],
    normalize_provider_fn: Callable[[Any], str | None],
    resolve_connection_region_fn: Callable[[Any], str],
    background_job_model: Any,
    job_type: Any,
    job_status: Any,
    insert_fn: Callable[[Any], Any],
    scheduler_job_runs: Any,
    scheduler_job_duration: Any,
    datetime_cls: Any,
    timezone_obj: Any,
    timedelta_cls: Any,
    uuid_cls: type[Any],
    asyncio_module: Any,
    inspect_module: Any,
    time_module: Any,
    recoverable_errors: tuple[type[BaseException], ...],
) -> None:
    job_name = "weekly_remediation_sweep"
    start_time = time_module.time()
    max_retries = 3
    retry_count = 0

    with scheduler_span_fn("scheduler.remediation_sweep", job_name=job_name):
        while retry_count < max_retries:
            try:
                async with open_db_session_fn() as db:
                    begin_ctx = db.begin()
                    if (
                        asyncio_module.iscoroutine(begin_ctx)
                        or inspect_module.isawaitable(begin_ctx)
                    ) and not hasattr(begin_ctx, "__aenter__"):
                        begin_ctx = await begin_ctx
                    async with begin_ctx:
                        with scheduler_span_fn(
                            "scheduler.remediation_sweep.load_connections",
                            retry_count=retry_count,
                        ):
                            connections = await list_active_connections_all_tenants_fn(
                                db,
                                with_for_update=True,
                                skip_locked=True,
                            )
                            connections = [
                                conn
                                for conn in connections
                                if is_connection_active_fn(conn)
                            ]
                            connection_limit = system_sweep_connection_limit_fn()
                            connections = cap_scope_items_fn(
                                connections,
                                scope="remediation_connections",
                                limit=connection_limit,
                            )

                        now = datetime_cls.now(timezone_obj.utc)
                        bucket_str = now.strftime("%Y-W%U")
                        jobs_to_insert: list[dict[str, Any]] = []
                        orchestrator = scheduler_orchestrator_cls(async_session_maker_fn)

                        for conn in connections:
                            resolved_provider = resolve_provider_from_connection_fn(conn)
                            provider = normalize_provider_fn(resolved_provider)
                            if not provider:
                                logger.warning(
                                    "remediation_sweep_skipping_unknown_provider",
                                    provider=resolved_provider or None,
                                    connection_id=str(getattr(conn, "id", "unknown")),
                                    tenant_id=str(getattr(conn, "tenant_id", "unknown")),
                                )
                                continue
                            connection_id = getattr(conn, "id", None)
                            tenant_id = getattr(conn, "tenant_id", None)
                            if not isinstance(connection_id, uuid_cls) or not isinstance(
                                tenant_id, uuid_cls
                            ):
                                logger.warning(
                                    "remediation_sweep_skipping_invalid_connection_identity",
                                    provider=provider,
                                    connection_id=str(connection_id),
                                    tenant_id=str(tenant_id),
                                )
                                continue
                            connection_region = resolve_connection_region_fn(conn)

                            is_green = True
                            if connection_region != "global":
                                is_green = await orchestrator.is_low_carbon_window(
                                    connection_region
                                )

                            scheduled_time = now
                            if not is_green:
                                scheduled_time += timedelta_cls(hours=4)

                            dedup_key = (
                                f"{tenant_id}:{provider}:{connection_id}:"
                                f"{job_type.REMEDIATION.value}:{bucket_str}"
                            )
                            jobs_to_insert.append(
                                {
                                    "job_type": job_type.REMEDIATION.value,
                                    "tenant_id": tenant_id,
                                    "payload": {
                                        "provider": provider,
                                        "connection_id": str(connection_id),
                                        "region": connection_region,
                                    },
                                    "status": job_status.PENDING,
                                    "scheduled_for": scheduled_time,
                                    "created_at": now,
                                    "deduplication_key": dedup_key,
                                }
                            )

                        jobs_enqueued = 0
                        if jobs_to_insert:
                            with scheduler_span_fn(
                                "scheduler.remediation_sweep.insert_jobs",
                                connection_count=len(connections),
                                job_count=len(jobs_to_insert),
                            ):
                                for i in range(0, len(jobs_to_insert), 500):
                                    chunk = jobs_to_insert[i : i + 500]
                                    stmt = (
                                        insert_fn(background_job_model)
                                        .values(chunk)
                                        .on_conflict_do_nothing(
                                            index_elements=["deduplication_key"]
                                        )
                                    )
                                    result_proxy = await db.execute(stmt)
                                    if hasattr(result_proxy, "rowcount"):
                                        jobs_enqueued += result_proxy.rowcount

                        logger.info(
                            "auto_remediation_sweep_completed",
                            count=len(connections),
                            jobs_enqueued=jobs_enqueued,
                        )

                scheduler_job_runs.labels(job_name=job_name, status="success").inc()
                break
            except recoverable_errors as exc:
                retry_count += 1
                logger.error(
                    "auto_remediation_sweep_failed",
                    error=str(exc),
                    attempt=retry_count,
                )
                if retry_count == max_retries:
                    scheduler_job_runs.labels(job_name=job_name, status="failure").inc()
                else:
                    await asyncio_module.sleep(2 ** (retry_count - 1))

        duration = time_module.time() - start_time
        scheduler_job_duration.labels(job_name=job_name).observe(duration)
