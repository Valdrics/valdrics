from __future__ import annotations

_CLOUD_PROVIDER_DISPLAY = {
    "aws": "Amazon Web Services",
    "azure": "Microsoft Azure",
    "gcp": "Google Cloud",
}

_VENDOR_DISPLAY_OVERRIDES = {
    "microsoft_365": "Microsoft 365",
    "office365": "Microsoft 365",
    "m365": "Microsoft 365",
}

_CANONICAL_TO_SERVICE_CATEGORY = {
    "compute": "Compute",
    "storage": "Storage",
    "network": "Networking",
    "database": "Databases",
}


def _humanize_vendor(vendor: str | None) -> str | None:
    if not isinstance(vendor, str):
        return None
    key = vendor.strip().lower()
    if not key:
        return None
    if key in _VENDOR_DISPLAY_OVERRIDES:
        return _VENDOR_DISPLAY_OVERRIDES[key]
    return " ".join(
        part.capitalize() for part in key.replace("_", " ").replace("-", " ").split()
    )


def _service_provider_display(provider_key: str, vendor: str | None = None) -> str:
    vendor_display = _humanize_vendor(vendor)
    if vendor_display:
        return vendor_display
    return _CLOUD_PROVIDER_DISPLAY.get(
        provider_key, provider_key.upper() if provider_key else "Unknown"
    )


def _focus_service_category(canonical_category: str | None) -> str:
    key = (canonical_category or "").strip().lower()
    return _CANONICAL_TO_SERVICE_CATEGORY.get(key, "Other")


def _focus_service_subcategory(service_category: str) -> str:
    # FOCUS allows explicit "Other (...)" subcategories per ServiceCategory.
    normalized = service_category.strip() or "Other"
    return f"Other ({normalized})"


def _focus_charge_category(service: str | None, usage_type: str | None) -> str:
    combined = f"{service or ''} {usage_type or ''}".strip().lower()
    if "tax" in combined:
        return "Tax"
    if "credit" in combined or "refund" in combined:
        return "Credit"
    if any(
        token in combined
        for token in ("support", "adjust", "adjustment", "fee", "marketplace")
    ):
        return "Adjustment"
    return "Usage"


def _focus_charge_frequency(charge_category: str) -> str:
    normalized = (charge_category or "").strip()
    if normalized in {"Usage", "Tax"}:
        return "Usage-Based"
    return "One-Time"
