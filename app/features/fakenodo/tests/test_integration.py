"""HTTP integration tests for the fakenodo feature.

Drive the application through the Flask test client. The ``test_client``
fixture rebuilds a clean DB per test for full isolation.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.features.fakenodo import routes as fakenodo_routes

pytestmark = pytest.mark.integration


mock_deposition_id = 1
mock_deposition_doi = "test-fakenodo-DOI"


def _create_mock_deposition():
    return MagicMock(id=mock_deposition_id, doi=mock_deposition_doi)


def _assert_mock_deposition_in_response(response):
    body = response.get_json()
    assert body["id"] == mock_deposition_id
    assert body["doi"] == mock_deposition_doi


def test_fakenodo_index_responds(test_client):
    response = test_client.get("/fakenodo")
    assert response.status_code == 200, "/fakenodo did not return 200"


# --- GET /<id>: get a deposition (and its DOI) ---


def test_fakenodo_get_deposition_by_id_success(test_client):
    mock_deposition = _create_mock_deposition()

    with patch.object(fakenodo_routes.fakenodo_service, "get_or_404", return_value=mock_deposition):
        response = test_client.get("/fakenodo/1")

    assert response.status_code == 200
    _assert_mock_deposition_in_response(response)


def test_fakenodo_get_deposition_by_id_not_found_returns_404(test_client):
    assert test_client.get("/fakenodo/999999").status_code == 404


# --- POST /: create a deposition ---


def test_fakenodo_create_deposition_success(test_client):
    mock_deposition = _create_mock_deposition()
    metadata = {}

    with patch.object(fakenodo_routes.fakenodo_service, "create", return_value=mock_deposition):
        response = test_client.post("/fakenodo", json=metadata)

    assert response.status_code == 201
    _assert_mock_deposition_in_response(response)


def test_fakenodo_create_deposition_without_metadata_returns_400(test_client):
    assert test_client.post("/fakenodo").status_code == 400
