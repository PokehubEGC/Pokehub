from datetime import datetime, timedelta

import pytest

from app import db
from app.features.auth.models import User
from app.features.dataset.models import Author, DataSet, DSDownloadRecord, DSMetaData, DSViewRecord

pytestmark = pytest.mark.integration


def test_home_page_renders_with_statistics(test_client):
    response = test_client.get("/")

    assert response.status_code == 200
    assert response.cache_control.no_store


def test_home_page_filters_trending_datasets_and_displays_public_author_credits(test_client, monkeypatch):
    monkeypatch.setattr(
        "app.features.public.routes.DataSetService.get_top_5_datasets_by_feature_model_count", lambda self: []
    )
    user = User.query.filter_by(email="test@example.com").one()
    now = datetime(2026, 11, 21, 12)

    class FixedClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now.replace(tzinfo=tz)

    monkeypatch.setattr("app.features.dataset.services.datetime", FixedClock)
    dataset = DataSet(
        user_id=user.id,
        ds_meta_data=DSMetaData(
            title="Popular downloads",
            description="Example",
            dataset_doi="10.1/downloads",
            authors=[Author(name="Zoe"), Author(name="Ana")],
        ),
    )
    anonymous = DataSet(
        user_id=user.id,
        ds_meta_data=DSMetaData(
            title="Popular views",
            description="Example",
            dataset_doi="10.1/views",
            dataset_anonymous=True,
            authors=[Author(name="Hidden author")],
        ),
    )
    db.session.add_all([dataset, anonymous])
    db.session.flush()
    db.session.add_all(
        [
            DSDownloadRecord(dataset_id=dataset.id, download_date=now - timedelta(days=1), download_cookie="d1"),
            DSViewRecord(dataset_id=anonymous.id, view_date=now - timedelta(days=20), view_cookie="v1"),
            DSViewRecord(dataset_id=anonymous.id, view_date=now - timedelta(days=30), view_cookie="v2"),
            DSViewRecord(dataset_id=anonymous.id, view_date=now - timedelta(days=31), view_cookie="v3"),
        ]
    )
    db.session.commit()

    default = test_client.get("/")
    assert default.status_code == 200
    html = default.get_data(as_text=True)
    assert "Trending datasets" in html
    assert "Popular downloads" in html
    assert "Ana, Zoe" in html
    assert "1 download" in " ".join(html.split())
    assert "Popular views" not in html

    weekly = test_client.get("/?trending_metric=views")
    assert weekly.status_code == 200
    assert "No views recorded" in weekly.get_data(as_text=True)

    monthly = test_client.get("/?trending_metric=views&trending_period=month")
    assert monthly.status_code == 200
    html = monthly.get_data(as_text=True)
    assert 'value="views" selected' in html
    assert 'value="month" selected' in html
    assert "Popular views" in html
    assert "Anonymous" in html
    assert "Hidden author" not in html
    assert "2 views" in " ".join(html.split())
    assert "Popular downloads" not in html

    db.session.add(DSViewRecord(dataset_id=anonymous.id, view_date=now, view_cookie="v4"))
    db.session.commit()

    refreshed = test_client.get("/?trending_metric=views&trending_period=month")
    assert refreshed.status_code == 200
    assert refreshed.cache_control.no_store
    assert "3 views" in " ".join(refreshed.get_data(as_text=True).split())
