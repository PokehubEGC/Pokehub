from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from app import db
from app.features.auth.models import User
from app.features.dataset.models import DataSet, DSMetaData
from app.features.featuremodel.models import FeatureModel
from app.features.hubfile.models import Hubfile, HubfileDownloadRecord, ModelCartItem

pytestmark = pytest.mark.integration


@pytest.fixture
def make_model(test_client, tmp_path, monkeypatch):
    monkeypatch.setenv("WORKING_DIR", str(tmp_path))
    owner = User.query.filter_by(email="test@example.com").one()

    def create(name, *, directory="", dataset=None, public=True):
        if dataset is None:
            metadata = DSMetaData(
                title="Cart dataset",
                description="Models for the cart",
                dataset_doi="10.1234/cart" if public else None,
            )
            dataset = DataSet(user_id=owner.id, ds_meta_data=metadata)
            db.session.add(dataset)
            db.session.flush()

        model = FeatureModel(dataset_id=dataset.id)
        db.session.add(model)
        db.session.flush()
        file = Hubfile(
            name=name,
            directory_path=directory,
            checksum="test",
            size=10,
            feature_model_id=model.id,
            dataset=dataset,
        )
        db.session.add(file)
        db.session.commit()

        path = tmp_path / "uploads" / f"user_{owner.id}" / f"dataset_{dataset.id}" / "uvl" / directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"features\n    {name}", encoding="utf-8")
        return file

    return create


def update(client, file_id, in_cart):
    return client.post(f"/model-cart/items/{file_id}", json={"in_cart": in_cart})


def test_guest_cart_add_remove_and_keep_selection_in_session(test_app, make_model):
    file = make_model("guest.uvl")
    client = test_app.test_client()
    assert client.get("/model-cart/items").json == {"ids": []}
    assert update(client, file.id, True).json == {"ids": [file.id]}
    assert update(client, file.id, True).json == {"ids": [file.id]}
    assert b"guest.uvl" in client.get("/model-cart").data
    assert test_app.test_client().get("/model-cart/items").json == {"ids": []}
    assert update(client, file.id, False).json == {"ids": []}
    assert update(client, file.id, False).json == {"ids": []}
    assert client.get("/model-cart/download").status_code == 302


def test_account_cart_persists_and_respects_dataset_access(test_app, make_model):
    file = make_model("draft.uvl", public=False)
    file_id = file.id
    first = test_app.test_client()
    assert update(first, file_id, True).status_code == 404

    credentials = {"email": "test@example.com", "password": "test1234"}
    assert first.post("/login", data=credentials).status_code == 302
    assert update(first, file_id, True).json == {"ids": [file_id]}
    assert update(first, file_id, True).json == {"ids": [file_id]}
    assert ModelCartItem.query.filter_by(file_id=file_id).count() == 1
    first.get("/logout")
    assert first.get("/model-cart/items").json == {"ids": []}

    second = test_app.test_client()
    assert second.post("/login", data=credentials).status_code == 302
    assert second.get("/model-cart/items").json == {"ids": [file_id]}
    assert update(second, file_id, False).json == {"ids": []}
    assert ModelCartItem.query.filter_by(file_id=file_id).count() == 0


def test_cart_download_contains_only_selected_files_and_records_them(test_app, make_model):
    first = make_model("shared.uvl", directory="nested")
    second = make_model("shared.uvl")
    make_model("unselected.uvl", dataset=first.dataset)
    client = test_app.test_client()
    update(client, first.id, True)
    update(client, second.id, True)

    assert client.head("/model-cart/download").status_code == 200
    assert HubfileDownloadRecord.query.filter(HubfileDownloadRecord.file_id.in_([first.id, second.id])).count() == 0
    with client.get("/model-cart/download") as response:
        assert response.status_code == 200
        assert response.mimetype == "application/zip"
        assert "attachment; filename=models.zip" in response.headers["Content-Disposition"]
        with ZipFile(BytesIO(response.data)) as archive:
            assert set(archive.namelist()) == {
                f"dataset_{first.dataset_id}/nested/shared.uvl",
                f"dataset_{second.dataset_id}/shared.uvl",
            }
            for name in archive.namelist():
                assert archive.read(name) == b"features\n    shared.uvl"

    with client.get("/model-cart/download") as response:
        assert response.status_code == 200
    cookie = client.get_cookie("file_download_cookie").value
    records = HubfileDownloadRecord.query.filter_by(download_cookie=cookie).all()
    assert sorted(record.file_id for record in records) == sorted([first.id, second.id])


def test_missing_file_does_not_record_a_partial_download(test_app, make_model):
    available = make_model("available.uvl")
    missing = make_model("missing.uvl", dataset=available.dataset)
    client = test_app.test_client()
    update(client, available.id, True)
    update(client, missing.id, True)
    Path(missing.get_full_path()).unlink()
    assert client.get("/model-cart/download").status_code == 302
    assert client.get_cookie("file_download_cookie") is None
    assert HubfileDownloadRecord.query.filter_by(file_id=available.id).count() == 0
