from io import BytesIO

import pandas as pd
from fastapi.testclient import TestClient

import main


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
    assert script.status_code == 200
    assert "loadDatasets" in script.text


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
    preview = client.get(f"/api/datasets/{dataset_id}/preview?limit=1")

    assert listing.status_code == 200
    assert listing.json()["datasets"][0]["dataset_id"] == dataset_id
    assert profile.status_code == 200
    assert profile.json()["profile"]["total_missing_values"] == 1
    assert preview.status_code == 200
    assert preview.json()["columns"] == ["name", "age"]
    assert preview.json()["rows"] == [{"name": "Ada", "age": 36}]


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
