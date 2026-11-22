import importlib.util
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest
import pytz
from werkzeug.datastructures import MultiDict

from app.features.dataset import routes as dataset_routes
from app.features.dataset.models import DataSet
from app.features.dataset.services import DatasetMetadataValidationError, DataSetService

pytestmark = pytest.mark.unit


def _dataset_for_type(doi=None, anonymous=False):
    return SimpleNamespace(ds_meta_data=SimpleNamespace(dataset_doi=doi, dataset_anonymous=anonymous))


def test_current_dataset_type_is_draft_without_doi():
    assert DataSetService._current_dataset_type(_dataset_for_type(doi=None)) == "draft"


def test_current_dataset_type_is_zenodo_with_doi():
    assert DataSetService._current_dataset_type(_dataset_for_type(doi="10.5072/zenodo.1")) == "zenodo"


def test_current_dataset_type_is_anonymous_when_flagged():
    ds = _dataset_for_type(doi="10.5072/zenodo.1", anonymous=True)
    assert DataSetService._current_dataset_type(ds) == "zenodo_anonymous"


# --- Dataset deletion window (is_deletable / can_be_deleted_by) -----------


def test_is_deletable_true_within_window():
    dataset = DataSet()
    dataset.created_at = datetime.now(pytz.utc) - timedelta(days=5)
    assert dataset.is_deletable() is True


def test_is_deletable_false_after_window():
    dataset = DataSet()
    dataset.created_at = datetime.now(pytz.utc) - timedelta(days=45)
    assert dataset.is_deletable() is False


def test_is_deletable_handles_naive_datetime():
    # MariaDB returns naive datetimes for DateTime columns; is_deletable must
    # not blow up comparing a naive value against an aware "now".
    dataset = DataSet()
    dataset.created_at = datetime.now() - timedelta(days=5)
    assert dataset.is_deletable() is True


def test_can_be_deleted_by_owner_within_window():
    dataset = DataSet()
    dataset.user_id = 1
    dataset.created_at = datetime.now(pytz.utc) - timedelta(days=5)
    owner = SimpleNamespace(id=1, is_authenticated=True)
    assert dataset.can_be_deleted_by(owner) is True


def test_can_be_deleted_by_rejects_non_owner():
    dataset = DataSet()
    dataset.user_id = 1
    dataset.created_at = datetime.now(pytz.utc) - timedelta(days=5)
    other_user = SimpleNamespace(id=2, is_authenticated=True)
    assert dataset.can_be_deleted_by(other_user) is False


def test_can_be_deleted_by_rejects_owner_after_window():
    dataset = DataSet()
    dataset.user_id = 1
    dataset.created_at = datetime.now(pytz.utc) - timedelta(days=45)
    owner = SimpleNamespace(id=1, is_authenticated=True)
    assert dataset.can_be_deleted_by(owner) is False


def test_can_be_deleted_by_rejects_unauthenticated_user():
    dataset = DataSet()
    dataset.user_id = 1
    dataset.created_at = datetime.now(pytz.utc) - timedelta(days=5)
    anon = SimpleNamespace(id=1, is_authenticated=False)
    assert dataset.can_be_deleted_by(anon) is False


def test_can_be_deleted_by_rejects_none_user():
    dataset = DataSet()
    dataset.user_id = 1
    dataset.created_at = datetime.now(pytz.utc) - timedelta(days=5)
    assert dataset.can_be_deleted_by(None) is False


def test_validate_orcid_invalid_format():
    with pytest.raises(DatasetMetadataValidationError, match="Invalid ORCID format"):
        DataSetService()._validate_orcid("12345")


def test_validate_orcid_invalid_checksum():
    service = DataSetService()
    with patch("app.features.dataset.services.urllib_request.urlopen") as mock_urlopen:
        with pytest.raises(DatasetMetadataValidationError, match="Invalid ORCID checksum"):
            service._validate_orcid("0000-0002-1825-0096")
        mock_urlopen.assert_not_called()


def test_validate_orcid_not_found():
    service = DataSetService()
    with patch(
        "app.features.dataset.services.urllib_request.urlopen",
        side_effect=HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None),
    ):
        with pytest.raises(DatasetMetadataValidationError, match="ORCID not found"):
            service._validate_orcid("0000-0002-1825-0097")


def test_resolve_download_formats_defaults_to_all_available():
    service = DataSetService()

    assert service.resolve_download_formats(None) == list(service.AVAILABLE_DOWNLOAD_FORMATS)


def test_resolve_download_formats_rejects_invalid_formats():
    with pytest.raises(ValueError, match="Invalid format"):
        DataSetService().resolve_download_formats(["uvl", "invalid_format"])


def test_resolve_download_formats_rejects_empty_selection():
    with pytest.raises(ValueError, match="No download formats selected"):
        DataSetService().resolve_download_formats(["   "])


def test_zip_from_storage_filters_files_by_selected_formats(tmp_path, monkeypatch):
    service = DataSetService()
    dataset = MagicMock()
    dataset.user_id = 42
    dataset.id = 99

    base = tmp_path / "uploads" / "user_42" / "dataset_99"
    (base / "uvl").mkdir(parents=True)
    (base / "glencoe").mkdir(parents=True)
    (base / "dimacs").mkdir(parents=True)
    (base / "uvl" / "model.uvl").write_text("uvl", encoding="utf-8")
    (base / "glencoe" / "model.json").write_text("json", encoding="utf-8")
    (base / "dimacs" / "model.cnf").write_text("cnf", encoding="utf-8")

    monkeypatch.setenv("WORKING_DIR", str(tmp_path))

    zip_path = service.zip_from_storage(dataset, formats=["uvl", "dimacs"])

    with zipfile.ZipFile(zip_path, "r") as zipf:
        names = set(zipf.namelist())
    assert "uvl/model.uvl" in names
    assert "dimacs/model.cnf" in names
    assert "glencoe/model.json" not in names


def test_zip_all_datasets_by_formats_only_includes_selected_format(tmp_path, monkeypatch):
    service = DataSetService()
    monkeypatch.chdir(tmp_path)

    ds10 = tmp_path / "uploads" / "user_1" / "dataset_10"
    ds10.joinpath("uvl").mkdir(parents=True)
    ds10.joinpath("glencoe").mkdir(parents=True)
    ds10.joinpath("uvl", "a.uvl").write_text("a", encoding="utf-8")
    ds10.joinpath("glencoe", "a.json").write_text("a", encoding="utf-8")

    ds11 = tmp_path / "uploads" / "user_1" / "dataset_11"
    ds11.joinpath("glencoe").mkdir(parents=True)
    ds11.joinpath("glencoe", "b.json").write_text("b", encoding="utf-8")

    service.is_synchronized = MagicMock(side_effect=lambda dataset_id: dataset_id == 10)

    zip_path = tmp_path / "bulk.zip"
    service.zip_all_datasets_by_formats(str(zip_path), formats=["glencoe"])

    with zipfile.ZipFile(zip_path, "r") as zipf:
        names = set(zipf.namelist())
    assert "dataset_10/glencoe/a.json" in names
    assert "dataset_10/uvl/a.uvl" not in names
    assert not any(name.startswith("dataset_11/") for name in names)


def test_import_remote_uvl_to_temp_downloads_file(tmp_path):
    user = MagicMock()
    user.temp_folder.return_value = str(tmp_path / "temp")

    remote_response = MagicMock()
    remote_response.read.return_value = b"features\n    Root"
    urlopen_context = MagicMock()
    urlopen_context.__enter__.return_value = remote_response

    with patch.object(dataset_routes.urllib_request, "urlopen", return_value=urlopen_context):
        imported_file = dataset_routes._import_remote_uvl_to_temp(
            "https://www.uvlhub.io/doi/10.5281/zenodo.1/files/raw/editor_model.uvl",
            user,
        )

    assert imported_file["name"] == "editor_model.uvl"
    assert imported_file["serverFilename"].endswith("_editor_model.uvl")
    saved_path = tmp_path / "temp" / imported_file["serverFilename"]
    assert saved_path.exists()
    assert saved_path.read_text(encoding="utf-8") == "features\n    Root"


# --- Optional author data on the API upload ------------------------------


def test_normalize_authors_returns_empty_list_for_none():
    assert DataSetService().normalize_authors(None) == []


def test_normalize_authors_cleans_and_keeps_every_field():
    # verify_orcid_ownership=False keeps this a pure unit test: the ownership
    # check reads the orcid table, and a unit test must not touch the database.
    authors = DataSetService().normalize_authors(
        [{"name": "  Lovelace, Ada ", "affiliation": " Analytical Engine ", "orcid": "0000-0002-1825-0097"}],
        verify_orcid_ownership=False,
    )

    assert authors == [{"name": "Lovelace, Ada", "affiliation": "Analytical Engine", "orcid": "0000-0002-1825-0097"}]


def test_normalize_authors_accepts_orcid_urls():
    authors = DataSetService().normalize_authors(
        [{"name": "Ada", "orcid": "https://orcid.org/0000-0002-1825-0097"}],
        verify_orcid_ownership=False,
    )

    assert authors[0]["orcid"] == "0000-0002-1825-0097"
    assert authors[0]["affiliation"] == ""


def test_normalize_authors_strips_control_and_bidi_characters():
    # A right-to-left override in a name renders as something else entirely on
    # the Zenodo record and on the dataset page, and newlines or tabs split a
    # one-line credit. Neither may survive into a permanent public record.
    authors = DataSetService().normalize_authors(
        [{"name": "Bad‮Name\nwith newline\tand tab", "affiliation": "Uni​versity"}],
        verify_orcid_ownership=False,
    )

    assert authors[0]["name"] == "BadName with newline and tab"
    assert authors[0]["affiliation"] == "University"


def test_normalize_authors_rejects_a_name_made_only_of_control_characters():
    with pytest.raises(DatasetMetadataValidationError, match="must have a name"):
        DataSetService().normalize_authors([{"name": "‮​"}], verify_orcid_ownership=False)


def test_normalize_authors_validates_orcid_offline():
    # No call to orcid.org: a publication must not depend on that service.
    with patch("app.features.dataset.services.urllib_request.urlopen") as mock_urlopen:
        with pytest.raises(DatasetMetadataValidationError, match="Invalid ORCID"):
            DataSetService().normalize_authors([{"name": "Ada", "orcid": "0000-0002-1825-0096"}])
        mock_urlopen.assert_not_called()


def test_normalize_authors_requires_a_name():
    with pytest.raises(DatasetMetadataValidationError, match="must have a name"):
        DataSetService().normalize_authors([{"affiliation": "Uni"}])


def test_normalize_authors_rejects_a_non_list_payload():
    with pytest.raises(DatasetMetadataValidationError, match="list of author objects"):
        DataSetService().normalize_authors({"name": "Ada"})


def test_normalize_authors_rejects_duplicate_orcid():
    with pytest.raises(DatasetMetadataValidationError, match="Duplicate author"):
        DataSetService().normalize_authors(
            [
                {"name": "Ada", "orcid": "0000-0002-1825-0097"},
                {"name": "Ada Lovelace", "orcid": "0000-0002-1825-0097"},
            ],
            verify_orcid_ownership=False,
        )


def test_normalize_authors_rejects_duplicate_name_and_affiliation():
    with pytest.raises(DatasetMetadataValidationError, match="same name and affiliation"):
        DataSetService().normalize_authors(
            [{"name": "Ada", "affiliation": "Uni"}, {"name": " ada ", "affiliation": "uni"}]
        )


def test_normalize_authors_rejects_too_many_authors():
    with pytest.raises(DatasetMetadataValidationError, match="Too many authors"):
        DataSetService().normalize_authors([{"name": f"Author {index}"} for index in range(26)])


def test_normalize_authors_rejects_an_oversized_name():
    with pytest.raises(DatasetMetadataValidationError, match="name is too long"):
        DataSetService().normalize_authors([{"name": "a" * 121}])


def test_extract_authors_from_request_prefers_the_json_body():
    authors = DataSetService().extract_authors_from_request({"authors": [{"name": "Ada"}]}, MultiDict())

    assert authors[0]["name"] == "Ada"


def test_extract_authors_from_request_reads_a_json_form_field():
    form_data = MultiDict([("authors", '[{"name": "Ada", "affiliation": "Uni"}]')])

    authors = DataSetService().extract_authors_from_request(None, form_data)

    assert authors == [{"name": "Ada", "affiliation": "Uni", "orcid": ""}]


def test_extract_authors_from_request_rejects_a_malformed_json_form_field():
    with pytest.raises(DatasetMetadataValidationError, match="JSON array"):
        DataSetService().extract_authors_from_request(None, MultiDict([("authors", "not json")]))


def test_extract_authors_from_request_reads_indexed_form_fields():
    form_data = MultiDict([("authors[0][name]", "Ada"), ("authors[0][affiliation]", "Uni")])

    authors = DataSetService().extract_authors_from_request(None, form_data)

    assert authors == [{"name": "Ada", "affiliation": "Uni", "orcid": ""}]


def test_extract_authors_from_request_returns_none_without_author_data():
    assert DataSetService().extract_authors_from_request({"title": "t"}, MultiDict()) is None


@pytest.mark.parametrize("value", [12345, 1.5, True, ["0000-0002-1825-0097"], {"orcid": "x"}])
def test_normalize_orcid_rejects_a_non_string_instead_of_crashing(value):
    # JSON puts no constraint on the type of this field. (value or "").strip()
    # raised AttributeError on every one of these, and the upload route only
    # catches DatasetMetadataValidationError, so the request came back a 500.
    with pytest.raises(DatasetMetadataValidationError, match="text value"):
        DataSetService()._normalize_orcid(value)


def test_normalize_orcid_still_accepts_none_and_strings():
    service = DataSetService()

    assert service._normalize_orcid(None) == ""
    assert service._normalize_orcid("  ") == ""
    assert service._normalize_orcid("https://orcid.org/0000-0002-1825-0097") == "0000-0002-1825-0097"


@pytest.mark.parametrize("value", [12345, 1.5, True, ["0000-0002-1825-0097"], {"orcid": "x"}])
def test_normalize_authors_rejects_a_non_string_orcid(value):
    with pytest.raises(DatasetMetadataValidationError, match="Invalid ORCID for author"):
        DataSetService().normalize_authors([{"name": "A", "orcid": value}])


# --- Version lineage payloads --------------------------------------------


def _version(dataset_id, version, doi, concept_doi=None, created_at=datetime(2026, 7, 1, 10, 0, 0)):
    return SimpleNamespace(
        id=dataset_id,
        dataset_version=version,
        created_at=created_at,
        ds_meta_data=SimpleNamespace(dataset_doi=doi, dataset_concept_doi=concept_doi),
    )


def test_api_lineage_payload_marks_only_the_newest_version_as_latest():
    lineage = [
        _version(1, 1, "10.5072/zenodo.1", concept_doi="10.5072/zenodo.0"),
        _version(2, 2, "10.5072/zenodo.2", concept_doi="10.5072/zenodo.0"),
    ]

    payload = dataset_routes._api_lineage_payload(lineage)

    assert payload["concept_doi"] == "10.5072/zenodo.0"
    assert payload["total_versions"] == 2
    assert payload["latest"] == {"dataset_id": 2, "version": 2, "doi": "10.5072/zenodo.2"}
    assert [entry["is_latest"] for entry in payload["versions"]] == [False, True]


def test_api_lineage_payload_borrows_the_concept_doi_from_any_version():
    # Versions published before the concept DOI was stored keep a null column;
    # a newer sibling answers for the whole lineage.
    lineage = [_version(1, 1, "10.5072/zenodo.1"), _version(2, 2, "10.5072/zenodo.2", "10.5072/zenodo.0")]

    assert dataset_routes._api_lineage_payload(lineage)["concept_doi"] == "10.5072/zenodo.0"


def test_api_version_entry_has_no_publication_date_without_doi():
    entry = dataset_routes._api_version_entry(_version(3, 1, None), latest_id=3)

    assert entry["publication_date"] is None
    assert entry["created_at"] == "2026-07-01T10:00:00"
    assert entry["is_latest"] is True


def test_api_latest_of_skips_a_version_that_was_never_published():
    # A clone whose Zenodo publication failed sits at the end of the lineage
    # with no DOI. Advertising it as the newest record would send clients at
    # something that does not exist on Zenodo.
    lineage = [_version(1, 1, "10.5072/zenodo.1"), _version(2, 2, None)]

    payload = dataset_routes._api_lineage_payload(lineage)

    assert payload["latest"] == {"dataset_id": 1, "version": 1, "doi": "10.5072/zenodo.1"}
    assert [entry["is_latest"] for entry in payload["versions"]] == [True, False]


def test_api_latest_of_falls_back_to_the_newest_when_nothing_is_published():
    lineage = [_version(1, 1, None), _version(2, 2, None)]

    assert dataset_routes._api_latest_of(lineage).id == 2


# --- Transfer target parsing ---------------------------------------------


def test_parse_strict_int_accepts_whole_numbers_in_both_shapes():
    assert dataset_routes._parse_strict_int(7) == 7
    assert dataset_routes._parse_strict_int("7") == 7
    assert dataset_routes._parse_strict_int(" -7 ") == -7


@pytest.mark.parametrize("value", [True, False, 1.9, 1.0, "1.9", "", "  ", "seven", None, [1], {"id": 1}])
def test_parse_strict_int_rejects_anything_that_is_not_a_whole_number(value):
    # int(True) is 1 and int(1.9) is 1: a permissive cast would offer the
    # dataset to whichever account holds that id instead of failing.
    assert dataset_routes._parse_strict_int(value) is None


# --- Migrations ----------------------------------------------------------


def _load_migration(module_name):
    path = Path(__file__).resolve().parents[4] / "migrations" / "versions" / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_transfer_migration_downgrade_drops_the_table_without_dropping_its_indexes():
    # MySQL and MariaDB back every foreign key with an index and refuse to drop
    # it while the constraint exists (error 1553), so dropping the indexes one
    # by one leaves the downgrade stuck halfway. Dropping the table takes its
    # indexes with it.
    #
    # This is a cheap ordering guard and nothing more: patching op means no
    # statement ever reaches an engine, so on its own it could not have caught
    # the original failure. The proof is
    # test_repository.py::test_transfer_migration_downgrades_on_a_real_database_with_rows,
    # which runs the real upgrade and downgrade against live MariaDB.
    migration = _load_migration("c9d0e1f2a3b4_add_api_publisher_and_transfers")

    with patch.object(migration, "op") as op:
        migration.downgrade()

    op.drop_table.assert_called_once_with("dataset_transfer_request")
    assert op.drop_index.call_args_list == []


# --- Popularity & download metrics ---------------------------------------


def test_dataset_download_and_view_count_methods():
    dataset = DataSet()
    dataset.id = 42

    with (
        patch("app.features.dataset.models.DSDownloadRecord.query") as mock_dl_query,
        patch("app.features.dataset.models.DSViewRecord.query") as mock_view_query,
    ):
        mock_dl_query.filter_by.return_value.count.return_value = 5
        mock_view_query.filter_by.return_value.count.return_value = 12

        assert dataset.get_download_count() == 5
        assert dataset.get_view_count() == 12

        mock_dl_query.filter_by.assert_called_once_with(dataset_id=42)
        mock_view_query.filter_by.assert_called_once_with(dataset_id=42)


def test_dataset_to_dict_includes_download_and_view_counts():
    dataset = DataSet()
    dataset.id = 10
    dataset.created_at = datetime(2026, 1, 1, tzinfo=pytz.utc)
    dataset.ds_meta_data = MagicMock(
        title="Test Dataset",
        description="A test",
        authors=[],
        publication_type=None,
        publication_doi=None,
        dataset_doi=None,
        dataset_concept_doi=None,
        metadata_synced=True,
        tags=None,
    )
    dataset.dataset_version = 1
    dataset.dataset_origin_id = None
    dataset.feature_models = []

    with (
        patch.object(dataset, "get_download_count", return_value=7),
        patch.object(dataset, "get_view_count", return_value=15),
        patch.object(dataset, "get_uvlhub_doi", return_value="http://uvlhub.io/dataset/10"),
        patch.object(dataset, "get_zenodo_url", return_value=None),
        patch.object(dataset, "get_file_total_size", return_value=0),
        patch.object(dataset, "get_file_total_size_for_human", return_value="0 bytes"),
    ):
        d = dataset.to_dict()

    assert d["download_count"] == 7
    assert d["downloads"] == 7
    assert d["view_count"] == 15
    assert d["views"] == 15
    assert d["download"] == "/dataset/download/10"
    dataset.get_download_count.assert_called_once()
    dataset.get_view_count.assert_called_once()


def test_update_dataset_metrics():
    from app.features.elasticsearch.utils import update_dataset_metrics

    # Case 1: dataset without DOI is skipped
    ds_no_doi = MagicMock()
    ds_no_doi.ds_meta_data.dataset_doi = None
    update_dataset_metrics(ds_no_doi)

    # Case 2: dataset with DOI updates Elasticsearch
    ds = MagicMock(id=12)
    ds.ds_meta_data.dataset_doi = "10.1234/test"
    ds.get_download_count.return_value = 8
    ds.get_view_count.return_value = 20

    with patch("app.features.elasticsearch.services.ElasticsearchService") as mock_es_cls:
        mock_es = MagicMock()
        mock_es.index_name = "search_index"
        mock_es_cls.return_value = mock_es

        update_dataset_metrics(ds)

        mock_es.es.update.assert_called_once_with(
            index="search_index",
            id="dataset-12",
            doc={
                "download_count": 8,
                "downloads": 8,
                "view_count": 20,
                "views": 20,
            },
            refresh=True,
        )


def test_get_dataset_stats_service():
    service = DataSetService()
    mock_ds = MagicMock(id=99)
    service.get_or_404 = MagicMock(return_value=mock_ds)
    service.dsdownloadrecord_repository.count_by_dataset = MagicMock(return_value=3)
    service.dsviewrecord_repository.count_by_dataset = MagicMock(return_value=10)
    service.dsdownloadrecord_repository.get_monthly_downloads_by_dataset = MagicMock(return_value={"2026-01": 3})
    service.dsviewrecord_repository.get_monthly_views_by_dataset = MagicMock(return_value={"2026-01": 10})

    stats = service.get_dataset_stats(99)

    assert stats["dataset_id"] == 99
    assert stats["total_downloads"] == 3
    assert stats["total_views"] == 10
    assert stats["downloads"] == 3
    assert stats["views"] == 10
    assert stats["downloads_per_month"] == {"2026-01": 3}
    assert stats["views_per_month"] == {"2026-01": 10}
