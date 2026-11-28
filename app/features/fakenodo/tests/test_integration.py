"""HTTP integration tests for the fakenodo feature.

Drive the application through the Flask test client. The ``test_client``
fixture rebuilds a clean DB per test for full isolation.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.features.fakenodo import routes as fakenodo_routes
from app.features.fakenodo.models import Deposition

pytestmark = pytest.mark.integration


mock_deposition_id = 1
mock_deposition_doi = "test-fakenodo-DOI"
mock_concept_doi = "10.5281/fakenodo.concept.1"


def _create_mock_deposition(status="draft", conceptdoi=None):
    return MagicMock(
        id=mock_deposition_id,
        doi=mock_deposition_doi,
        conceptdoi=conceptdoi,
        status=status,
    )


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


# --- GET /: list depositions ---


def test_fakenodo_list_depositions_empty(test_client):
    response = test_client.get("/fakenodo")
    assert response.status_code == 200
    assert response.get_json() == []


def test_fakenodo_list_depositions_with_items(test_client):
    mock_deposition = _create_mock_deposition(status="published", conceptdoi=mock_concept_doi)

    with patch.object(fakenodo_routes.fakenodo_service, "get_all", return_value=[mock_deposition]):
        response = test_client.get("/fakenodo")

    assert response.status_code == 200
    body = response.get_json()
    assert len(body) == 1
    assert body[0]["id"] == mock_deposition_id
    assert body[0]["doi"] == mock_deposition_doi
    assert body[0]["conceptdoi"] == mock_concept_doi
    assert body[0]["status"] == "published"


# --- DELETE /<id>: delete a deposition ---


def test_fakenodo_delete_deposition_success(test_client):
    with patch.object(fakenodo_routes.fakenodo_service, "delete", return_value=None) as mock_delete:
        response = test_client.delete(f"/fakenodo/{mock_deposition_id}")

    assert response.status_code == 204
    assert response.data == b""
    mock_delete.assert_called_once_with(mock_deposition_id)


def test_fakenodo_delete_deposition_not_found_returns_404(test_client):
    assert test_client.delete("/fakenodo/999999").status_code == 404


# --- POST /<id>/actions/publish: publish (returns a DOI) & versioning rules ---


def test_fakenodo_publish_not_found_returns_404(test_client):
    assert test_client.post("/fakenodo/999999/actions/publish").status_code == 404


def test_fakenodo_publish_first_time_generates_doi_and_conceptdoi(test_client):
    deposition = Deposition(id=1, doi=None, conceptdoi=None, status="draft", files_changed=True)

    def fake_update(dep_id, **kwargs):
        for key, value in kwargs.items():
            setattr(deposition, key, value)
        return deposition

    with (
        patch.object(fakenodo_routes.fakenodo_service.repository, "get_or_404", return_value=deposition),
        patch.object(fakenodo_routes.fakenodo_service.repository, "update", side_effect=fake_update),
    ):
        response = test_client.post("/fakenodo/1/actions/publish")

    assert response.status_code == 202
    body = response.get_json()
    assert body["status"] == "published"
    assert body["doi"] is not None
    assert body["conceptdoi"] == "10.5281/fakenodo.concept.1"


def test_fakenodo_publish_metadata_only_keeps_same_doi(test_client):
    deposition = Deposition(
        id=1,
        doi="10.5281/fakenodo.1.abc123",
        conceptdoi="10.5281/fakenodo.concept.1",
        status="draft",
        files_changed=False,
    )

    def fake_update(dep_id, **kwargs):
        for key, value in kwargs.items():
            setattr(deposition, key, value)
        return deposition

    with (
        patch.object(fakenodo_routes.fakenodo_service.repository, "get_or_404", return_value=deposition),
        patch.object(fakenodo_routes.fakenodo_service.repository, "update", side_effect=fake_update),
    ):
        response = test_client.post("/fakenodo/1/actions/publish")

    assert response.status_code == 202
    body = response.get_json()
    assert body["doi"] == "10.5281/fakenodo.1.abc123"
    assert body["conceptdoi"] == "10.5281/fakenodo.concept.1"


def test_fakenodo_publish_after_file_change_generates_new_doi_same_conceptdoi(test_client):
    deposition = Deposition(
        id=1,
        doi="10.5281/fakenodo.1.abc123",
        conceptdoi="10.5281/fakenodo.concept.1",
        status="draft",
        files_changed=True,
    )

    def fake_update(dep_id, **kwargs):
        for key, value in kwargs.items():
            setattr(deposition, key, value)
        return deposition

    with (
        patch.object(fakenodo_routes.fakenodo_service.repository, "get_or_404", return_value=deposition),
        patch.object(fakenodo_routes.fakenodo_service.repository, "update", side_effect=fake_update),
    ):
        response = test_client.post("/fakenodo/1/actions/publish")

    assert response.status_code == 202
    body = response.get_json()
    assert body["doi"] != "10.5281/fakenodo.1.abc123"
    assert body["conceptdoi"] == "10.5281/fakenodo.concept.1"


# --- POST /<id>/files: upload a file ---


def test_fakenodo_upload_file_success(test_client):
    deposition = Deposition(
        id=1,
        doi="10.5281/fakenodo.1.abc123",
        conceptdoi="10.5281/fakenodo.concept.1",
        status="draft",
        files_changed=False,
    )

    def fake_update(dep_id, **kwargs):
        for key, value in kwargs.items():
            setattr(deposition, key, value)
        return deposition

    file_data = {"name": "test.txt", "file": "This is a test file."}

    with (
        patch.object(fakenodo_routes.fakenodo_service.repository, "get_or_404", return_value=deposition),
        patch.object(fakenodo_routes.fakenodo_service.repository, "update", side_effect=fake_update),
    ):
        response = test_client.post("/fakenodo/1/files", json=file_data)

    assert response.status_code == 201
    assert response.get_json()["filename"] == "test.txt"
    assert deposition.files_changed


def test_fakenodo_upload_file_without_data_returns_400(test_client):
    assert test_client.post("/fakenodo/1/files").status_code == 400


def test_fakenodo_upload_file_without_file_returns_400(test_client):
    file_data = {"name": "test.txt"}
    assert test_client.post("/fakenodo/1/files", json=file_data).status_code == 400


def test_fakenodo_upload_file_without_file_name_returns_400(test_client):
    file_data = {"file": "This is a test file."}
    assert test_client.post("/fakenodo/1/files", json=file_data).status_code == 400


def test_fakenodo_upload_file_deposition_not_found_returns_404(test_client):
    file_data = {"name": "test.txt", "file": "This is a test file."}
    assert test_client.post("/fakenodo/999999/files", json=file_data).status_code == 404


# --- POST /<id>/actions/newversion: create a new version sharing conceptdoi ---


def test_fakenodo_newversion_not_found_returns_404(test_client):
    assert test_client.post("/fakenodo/999999/actions/newversion").status_code == 404


def test_fakenodo_newversion_creates_draft_with_same_conceptdoi(test_client):
    original = Deposition(
        id=1,
        doi="10.5281/fakenodo.1.abc123",
        conceptdoi="10.5281/fakenodo.concept.1",
        status="published",
        files_changed=False,
    )
    created_draft = Deposition(
        id=2,
        doi=None,
        conceptdoi="10.5281/fakenodo.concept.1",
        status="draft",
        files_changed=True,
    )

    with (
        patch.object(fakenodo_routes.fakenodo_service.repository, "get_or_404", return_value=original),
        patch.object(fakenodo_routes.fakenodo_service.repository, "create", return_value=created_draft) as mock_create,
    ):
        response = test_client.post("/fakenodo/1/actions/newversion")

    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] == 2
    assert body["doi"] is None
    assert body["conceptdoi"] == "10.5281/fakenodo.concept.1"
    assert body["status"] == "draft"
    mock_create.assert_called_once_with(
        doi=None,
        conceptdoi="10.5281/fakenodo.concept.1",
        status="draft",
        files_changed=True,
    )


def test_fakenodo_newversion_and_publish_generates_new_doi_same_conceptdoi(test_client):
    new_draft = Deposition(
        id=2,
        doi=None,
        conceptdoi="10.5281/fakenodo.concept.1",
        status="draft",
        files_changed=True,
    )

    def fake_update(dep_id, **kwargs):
        for key, value in kwargs.items():
            setattr(new_draft, key, value)
        return new_draft

    with (
        patch.object(fakenodo_routes.fakenodo_service.repository, "get_or_404", return_value=new_draft),
        patch.object(fakenodo_routes.fakenodo_service.repository, "update", side_effect=fake_update),
    ):
        response = test_client.post("/fakenodo/2/actions/publish")

    assert response.status_code == 202
    body = response.get_json()
    assert body["id"] == 2
    assert body["doi"] is not None
    assert body["doi"] != "10.5281/fakenodo.1.abc123"
    assert body["conceptdoi"] == "10.5281/fakenodo.concept.1"
    assert body["status"] == "published"
