"""Builds links to the Zenodo record from ZENODO_API_URL (single source of truth)."""

import os

_API_SUFFIX = "/api/deposit/depositions"


def _api_url() -> str:
    root = "https://zenodo.org" if os.getenv("FLASK_ENV") == "production" else "https://sandbox.zenodo.org"
    return os.getenv("ZENODO_API_URL", root + _API_SUFFIX).rstrip("/")


def zenodo_record_url(deposition_id) -> str | None:
    if not deposition_id:
        return None
    api_url = _api_url()
    if api_url.endswith(_API_SUFFIX):
        return f"{api_url[: -len(_API_SUFFIX)]}/record/{deposition_id}"
    return f"{api_url}/{deposition_id}"  