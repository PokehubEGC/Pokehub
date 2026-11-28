import pytest

from app.features.dataset.zenodo_links import zenodo_record_url

pytestmark = pytest.mark.unit


def test_real_zenodo_url(monkeypatch):
    monkeypatch.setenv("ZENODO_API_URL", "https://zenodo.org/api/deposit/depositions")
    assert zenodo_record_url(5) == "https://zenodo.org/record/5"


def test_sandbox_by_default_in_development(monkeypatch):
    monkeypatch.delenv("ZENODO_API_URL", raising=False)
    monkeypatch.setenv("FLASK_ENV", "development")
    assert zenodo_record_url(5) == "https://sandbox.zenodo.org/record/5"


def test_fakenodo_url(monkeypatch):
    monkeypatch.setenv("ZENODO_API_URL", "http://localhost/fakenodo")
    assert zenodo_record_url(5) == "http://localhost/fakenodo/5"


def test_no_deposition_returns_none():
    assert zenodo_record_url(None) is None
