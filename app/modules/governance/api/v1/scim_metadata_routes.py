from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.modules.governance.api.v1.scim_errors import ScimError
from app.modules.governance.api.v1.scim_schemas import (
    SCIM_GROUP_SCHEMA,
    SCIM_LIST_SCHEMA,
    SCIM_USER_SCHEMA,
    resource_types_response,
    scim_group_schema_resource as _scim_group_schema_resource,
    scim_user_schema_resource as _scim_user_schema_resource,
    service_provider_config,
)


async def get_service_provider_config() -> dict[str, Any]:
    return service_provider_config()


async def list_schemas(request: Request) -> dict[str, Any]:
    base_url = str(request.base_url).rstrip("/")
    resources = [
        _scim_user_schema_resource(base_url=base_url),
        _scim_group_schema_resource(base_url=base_url),
    ]
    return {
        "schemas": [SCIM_LIST_SCHEMA],
        "totalResults": len(resources),
        "startIndex": 1,
        "itemsPerPage": len(resources),
        "Resources": resources,
    }


async def get_schema(request: Request, schema_id: str) -> JSONResponse:
    base_url = str(request.base_url).rstrip("/")
    normalized = (schema_id or "").strip()
    if normalized == SCIM_USER_SCHEMA:
        return JSONResponse(
            status_code=200,
            content=_scim_user_schema_resource(base_url=base_url),
        )
    if normalized == SCIM_GROUP_SCHEMA:
        return JSONResponse(
            status_code=200,
            content=_scim_group_schema_resource(base_url=base_url),
        )
    raise ScimError(404, "Resource not found")


async def get_resource_types() -> dict[str, Any]:
    return resource_types_response()


def register_metadata_routes(router: APIRouter) -> None:
    router.add_api_route(
        "/ServiceProviderConfig", get_service_provider_config, methods=["GET"]
    )
    router.add_api_route("/Schemas", list_schemas, methods=["GET"])
    router.add_api_route("/Schemas/{schema_id:path}", get_schema, methods=["GET"])
    router.add_api_route("/ResourceTypes", get_resource_types, methods=["GET"])
