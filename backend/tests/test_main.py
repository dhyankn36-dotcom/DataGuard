from io import BytesIO
import sys

import pandas as pd
import pytest
from fastapi.testclient import TestClient as FastAPITestClient

import main

TestClient = FastAPITestClient


@pytest.fixture(autouse=True)
def isolated_authenticated_test_environment(monkeypatch, tmp_path):
    database_path = tmp_path.parent / f"{tmp_path.name}-dataguard.sqlite3"
    monkeypatch.setattr(main, "DATABASE_PATH", database_path)
    main.initialize_database()
    main.create_user(
        database_path,
        "admin@dataguard.test",
        "Secure-admin-password-123",
        role="admin",
    )

    def authenticated_client(app):
        client = FastAPITestClient(app)
        response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@dataguard.test",
                "password": "Secure-admin-password-123",
            },
        )
        assert response.status_code == 200
        return client

    monkeypatch.setattr(sys.modules[__name__], "TestClient", authenticated_client)


def test_api_requires_login_and_session_cookie():
    client = FastAPITestClient(main.app)

    assert client.get("/api/datasets").status_code == 401
    invalid_login = client.post(
        "/api/auth/login",
        json={"email": "admin@dataguard.test", "password": "wrong"},
    )
    assert invalid_login.status_code == 401

    login = client.post(
        "/api/auth/login",
        json={
            "email": "admin@dataguard.test",
            "password": "Secure-admin-password-123",
        },
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "admin"
    assert client.cookies.get("dataguard_session")
    assert "httponly" in login.headers["set-cookie"].lower()
    assert "samesite=lax" in login.headers["set-cookie"].lower()
    assert client.get("/api/auth/me").json()["user"]["email"] == "admin@dataguard.test"

    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_datasets_are_private_and_only_admins_can_create_accounts():
    admin = TestClient(main.app)
    created = admin.post(
        "/api/admin/users",
        json={
            "email": "analyst@dataguard.test",
            "password": "Secure-analyst-password-123",
        },
    )
    assert created.status_code == 201

    upload = admin.post(
        "/api/datasets/upload",
        files={"file": ("private.csv", b"name\nAda\n", "text/csv")},
    )
    dataset_id = upload.json()["dataset_id"]

    analyst = FastAPITestClient(main.app)
    login = analyst.post(
        "/api/auth/login",
        json={
            "email": "analyst@dataguard.test",
            "password": "Secure-analyst-password-123",
        },
    )
    assert login.status_code == 200
    assert analyst.get("/api/datasets").json()["datasets"] == []
    assert analyst.get(f"/api/datasets/{dataset_id}/profile").status_code == 404
    assert analyst.delete(f"/api/datasets/{dataset_id}").status_code == 404
    assert admin.get("/api/datasets").json()["datasets"][0]["filename"] == "private.csv"

    forbidden = analyst.post(
        "/api/admin/users",
        json={
            "email": "other@dataguard.test",
            "password": "Secure-other-password-123",
        },
    )
    assert forbidden.status_code == 403


def test_legacy_files_are_not_imported_or_deleted(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    legacy_file = tmp_path / "00000000-0000-0000-0000-000000000001.csv"
    legacy_file.write_text("name\nAda\n", encoding="utf-8")
    client = TestClient(main.app)

    assert client.get("/api/datasets").json()["datasets"] == []
    assert client.get(
        "/api/datasets/00000000-0000-0000-0000-000000000001/profile"
    ).status_code == 404
    assert legacy_file.exists()


def test_clean_export_fills_missing_values_and_removes_duplicates(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    client = TestClient(main.app)
    original = b"score,group\n1,a\n,\n5,c\n7,c\n7,c\n"
    upload = client.post(
        "/api/datasets/upload",
        files={"file": ("sample.csv", original, "text/csv")},
    )
    dataset_id = upload.json()["dataset_id"]

    response = client.get(
        f"/api/datasets/{dataset_id}/cleaned"
        "?missing_strategy=fill_median_mode&remove_duplicates=true"
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert f"dataguard-cleaned-{dataset_id}.csv" in response.headers[
        "content-disposition"
    ]
    assert response.headers["X-DataGuard-Original-Rows"] == "5"
    assert response.headers["X-DataGuard-Exported-Rows"] == "4"
    assert response.headers["X-DataGuard-Removed-Incomplete-Rows"] == "0"
    assert response.headers["X-DataGuard-Removed-Duplicate-Rows"] == "1"
    assert response.headers["X-DataGuard-Filled-Values"] == "2"
    cleaned = pd.read_csv(BytesIO(response.content))
    assert cleaned.to_dict(orient="records") == [
        {"score": 1.0, "group": "a"},
        {"score": 6.0, "group": "c"},
        {"score": 5.0, "group": "c"},
        {"score": 7.0, "group": "c"},
    ]
    assert (tmp_path / f"{dataset_id}.csv").read_bytes() == original


def test_clean_export_can_drop_incomplete_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    client = TestClient(main.app)
    upload = client.post(
        "/api/datasets/upload",
        files={
            "file": (
                "sample.csv",
                b"name,age\nAda,36\nGrace,\n",
                "text/csv",
            )
        },
    )

    response = client.get(
        f"/api/datasets/{upload.json()['dataset_id']}/cleaned"
        "?missing_strategy=drop_rows"
    )

    assert response.status_code == 200
    assert response.headers["X-DataGuard-Exported-Rows"] == "1"
    assert response.headers["X-DataGuard-Removed-Incomplete-Rows"] == "1"
    assert response.headers["X-DataGuard-Filled-Values"] == "0"
    assert pd.read_csv(BytesIO(response.content)).to_dict(orient="records") == [
        {"name": "Ada", "age": 36}
    ]


def test_clean_export_leaves_all_empty_columns_unfilled(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    client = TestClient(main.app)
    upload = client.post(
        "/api/datasets/upload",
        files={
            "file": (
                "sample.csv",
                b"score,notes\n1,\n3,\n",
                "text/csv",
            )
        },
    )

    response = client.get(
        f"/api/datasets/{upload.json()['dataset_id']}/cleaned"
        "?missing_strategy=fill_median_mode"
    )

    assert response.status_code == 200
    assert response.headers["X-DataGuard-Filled-Values"] == "0"
    cleaned = pd.read_csv(BytesIO(response.content))
    assert cleaned["notes"].isna().all()


def test_clean_export_rejects_unknown_missing_strategy():
    client = TestClient(main.app)

    response = client.get(
        "/api/datasets/00000000-0000-0000-0000-000000000000/cleaned"
        "?missing_strategy=guess"
    )

    assert response.status_code == 422


def test_upload_dataset_saves_valid_csv(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    client = TestClient(main.app)

    response = client.post(
        "/api/datasets/upload",
        files={"file": ("sample.csv", b"name,age\nAda,36\n", "text/csv")},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["rows"] == 1
    assert result["columns"] == 2
    assert result["column_names"] == ["name", "age"]
    assert (tmp_path / f'{result["dataset_id"]}.csv').exists()


def test_root_serves_workspace_and_static_assets():
    client = TestClient(main.app)

    page = client.get("/")
    script = client.get("/static/app.js")

    assert page.status_code == 200
    assert "DataGuard" in page.text
    assert "Completeness / missing" in page.text
    assert script.status_code == 200
    assert "loadDatasets" in script.text
    assert "column.missing_values" in script.text
    assert "} missing`" in script.text


def test_list_profile_and_preview_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    client = TestClient(main.app)
    upload = client.post(
        "/api/datasets/upload",
        files={
            "file": (
                "sample.csv",
                b"name,age\nAda,36\nGrace,\n",
                "text/csv",
            )
        },
    )
    dataset_id = upload.json()["dataset_id"]

    listing = client.get("/api/datasets")
    profile = client.get(f"/api/datasets/{dataset_id}/profile")
    preview = client.get(f"/api/datasets/{dataset_id}/preview?limit=1&offset=1")

    assert listing.status_code == 200
    assert listing.json()["datasets"][0]["dataset_id"] == dataset_id
    assert profile.status_code == 200
    assert profile.json()["profile"]["total_missing_values"] == 1
    assert preview.status_code == 200
    assert preview.json()["columns"] == ["name", "age"]
    assert preview.json()["rows"] == [{"name": "Grace", "age": None}]
    assert preview.json()["offset"] == 1
    assert preview.json()["has_more"] is False


def test_preview_paginates_xlsx_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    workbook = BytesIO()
    pd.DataFrame({"name": ["Ada", "Grace", "Lin"], "age": [36, 45, 28]}).to_excel(
        workbook,
        index=False,
    )
    client = TestClient(main.app)
    upload = client.post(
        "/api/datasets/upload",
        files={"file": ("sample.xlsx", workbook.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    dataset_id = upload.json()["dataset_id"]

    response = client.get(
        f"/api/datasets/{dataset_id}/preview?limit=1&offset=1"
    )

    assert response.status_code == 200
    assert response.json()["rows"] == [{"name": "Grace", "age": 45}]
    assert response.json()["has_more"] is True


def test_preview_rejects_excessive_offset():
    client = TestClient(main.app)

    response = client.get(
        "/api/datasets/00000000-0000-0000-0000-000000000000/preview?offset=1000001"
    )

    assert response.status_code == 422


def test_download_report_includes_dataset_metadata_and_profile(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    client = TestClient(main.app)
    upload = client.post(
        "/api/datasets/upload",
        files={
            "file": (
                "sample.csv",
                b"name,age\nAda,36\nGrace,\n",
                "text/csv",
            )
        },
    )
    dataset_id = upload.json()["dataset_id"]

    response = client.get(f"/api/datasets/{dataset_id}/report")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert f"dataguard-report-{dataset_id}.json" in response.headers[
        "content-disposition"
    ]
    report = response.json()
    assert report["dataset"] == {
        "dataset_id": dataset_id,
        "filename": "sample.csv",
        "rows": 2,
        "columns": 2,
    }
    assert report["profile"]["total_missing_values"] == 1
    assert report["generated_at"].endswith("+00:00")


def test_delete_dataset_removes_uploaded_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    client = TestClient(main.app)
    upload = client.post(
        "/api/datasets/upload",
        files={"file": ("sample.csv", b"name\nAda\n", "text/csv")},
    )
    dataset_id = upload.json()["dataset_id"]
    uploaded_file = tmp_path / f"{dataset_id}.csv"

    response = client.delete(f"/api/datasets/{dataset_id}")

    assert response.status_code == 200
    assert response.json()["dataset_id"] == dataset_id
    assert not uploaded_file.exists()
    assert client.get(f"/api/datasets/{dataset_id}/profile").status_code == 404


def test_delete_dataset_rejects_invalid_and_unknown_ids():
    client = TestClient(main.app)

    invalid = client.delete("/api/datasets/not-a-uuid")
    unknown = client.delete(
        "/api/datasets/00000000-0000-0000-0000-000000000000"
    )

    assert invalid.status_code == 400
    assert unknown.status_code == 404


def test_profile_marks_empty_and_constant_columns():
    dataframe = pd.DataFrame({
        "empty": [None, None],
        "constant": ["same", "same"],
        "varied": ["first", "second"],
    })

    profile = main.profile_dataset(dataframe)

    assert profile["columns"]["empty"]["is_empty"] is True
    assert profile["columns"]["empty"]["is_constant"] is False
    assert profile["columns"]["constant"]["is_empty"] is False
    assert profile["columns"]["constant"]["is_constant"] is True
    assert profile["columns"]["varied"]["is_constant"] is False


def test_profile_handles_infinite_numeric_values(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    client = TestClient(main.app)
    upload = client.post(
        "/api/datasets/upload",
        files={
            "file": (
                "infinite.csv",
                b"value\ninf\n-inf\n1\n2\n3\n4\n",
                "text/csv",
            )
        },
    )
    dataset_id = upload.json()["dataset_id"]

    response = client.get(f"/api/datasets/{dataset_id}/profile")

    assert response.status_code == 200
    numeric_column = response.json()["profile"]["columns"]["value"]
    assert numeric_column["non_finite_values"] == 2
    assert numeric_column["statistics"] == {
        "mean": 2.5,
        "median": 2.5,
        "minimum": 1.0,
        "maximum": 4.0,
    }


def test_upload_dataset_accepts_xlsx(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    workbook = BytesIO()
    pd.DataFrame({"name": ["Ada"], "age": [36]}).to_excel(
        workbook,
        index=False,
    )
    client = TestClient(main.app)

    response = client.post(
        "/api/datasets/upload",
        files={
            "file": (
                "sample.xlsx",
                workbook.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["rows"] == 1
    assert response.json()["columns"] == 2


def test_preview_rejects_invalid_id_and_limit():
    client = TestClient(main.app)

    invalid_id = client.get("/api/datasets/not-a-uuid/preview")
    invalid_limit = client.get(
        "/api/datasets/00000000-0000-0000-0000-000000000000/preview?limit=0"
    )

    assert invalid_id.status_code == 400
    assert invalid_limit.status_code == 422


def test_upload_dataset_rejects_oversized_file_without_saving(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(main, "MAX_FILE_SIZE", 5)
    client = TestClient(main.app)

    response = client.post(
        "/api/datasets/upload",
        files={"file": ("large.csv", b"name,age\nAda,36\n", "text/csv")},
    )

    assert response.status_code == 413
    assert list(tmp_path.iterdir()) == []


def test_upload_dataset_rejects_empty_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    client = TestClient(main.app)

    response = client.post(
        "/api/datasets/upload",
        files={"file": ("empty.csv", b"", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded file is empty."
    assert list(tmp_path.iterdir()) == []


def test_upload_dataset_rejects_unsupported_extension():
    client = TestClient(main.app)

    response = client.post(
        "/api/datasets/upload",
        files={"file": ("data.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only CSV and XLSX files are supported."
    )
