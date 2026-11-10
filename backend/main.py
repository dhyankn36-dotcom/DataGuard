import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Literal
import uuid

import pandas as pd
from app.services.profiling import profile_dataset
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "datasets"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

MAX_FILE_SIZE = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}

app = FastAPI(
    title="DataGuard API",
    description="Intelligent Data Quality Monitoring Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR / "static"),
    name="static",
)


@app.get("/")
def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health_check():
    return {"status": "healthy"}


def find_dataset(dataset_id: str) -> Path:
    try:
        normalized_id = str(uuid.UUID(dataset_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dataset ID.")

    for extension in ALLOWED_EXTENSIONS:
        candidate = UPLOAD_DIR / f"{normalized_id}{extension}"
        if candidate.is_file():
            return candidate

    raise HTTPException(status_code=404, detail="Dataset not found.")


def read_dataset(file_path: Path, **options) -> pd.DataFrame:
    if file_path.suffix.lower() == ".csv":
        return read_csv_content(file_path.read_bytes(), **options)
    return pd.read_excel(file_path, **options)


def read_csv_content(content: bytes, **options) -> pd.DataFrame:
    try:
        return pd.read_csv(BytesIO(content), encoding="utf-8-sig", **options)
    except UnicodeDecodeError:
        return pd.read_csv(BytesIO(content), encoding="cp1252", **options)


def prepare_cleaned_dataset(
    dataframe: pd.DataFrame,
    missing_strategy: str,
    remove_duplicates: bool,
) -> tuple[pd.DataFrame, int, int, int]:
    cleaned = dataframe.copy()
    removed_incomplete_rows = 0
    filled_values = 0

    if missing_strategy == "drop_rows":
        rows_before = len(cleaned)
        cleaned = cleaned.dropna()
        removed_incomplete_rows = rows_before - len(cleaned)
    elif missing_strategy == "fill_median_mode":
        missing_before = int(cleaned.isna().sum().sum())
        for column in cleaned.columns:
            series = cleaned[column]
            if not series.isna().any():
                continue

            if pd.api.types.is_numeric_dtype(series):
                finite_values = series[
                    series.notna()
                    & series.ne(float("inf"))
                    & series.ne(float("-inf"))
                ]
                fill_value = finite_values.median() if not finite_values.empty else None
            else:
                modes = series.mode(dropna=True)
                fill_value = modes.iloc[0] if not modes.empty else None

            if fill_value is not None:
                cleaned[column] = series.fillna(fill_value)
        filled_values = missing_before - int(cleaned.isna().sum().sum())

    duplicates_before = len(cleaned)
    if remove_duplicates:
        cleaned = cleaned.drop_duplicates()
    removed_duplicate_rows = duplicates_before - len(cleaned)

    return cleaned, removed_incomplete_rows, removed_duplicate_rows, filled_values


@app.get("/api/datasets")
def list_datasets():
    datasets = []
    for file_path in UPLOAD_DIR.iterdir():
        if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        try:
            dataset_id = str(uuid.UUID(file_path.stem))
        except ValueError:
            continue
        if not file_path.is_file():
            continue

        datasets.append({
            "dataset_id": dataset_id,
            "filename": file_path.name,
            "size_bytes": file_path.stat().st_size,
            "file_type": file_path.suffix[1:].upper(),
        })

    datasets.sort(key=lambda dataset: dataset["filename"])
    return {"datasets": datasets}


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id: str):
    file_path = find_dataset(dataset_id)
    file_path.unlink()
    return {
        "message": "Dataset deleted successfully",
        "dataset_id": str(uuid.UUID(dataset_id)),
    }


@app.post("/api/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)):
    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only CSV and XLSX files are supported."
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Maximum file size is 20 MB."
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty."
        )

    dataset_id = str(uuid.uuid4())
    filename = f"{dataset_id}{extension}"
    destination = UPLOAD_DIR / filename

    try:
        if extension == ".csv":
            dataframe = read_csv_content(content)
        else:
            dataframe = pd.read_excel(BytesIO(content))

        if dataframe.empty:
            raise ValueError("The dataset contains no records.")

        if len(dataframe.columns) == 0:
            raise ValueError("The dataset contains no columns.")

        destination.write_bytes(content)

    except Exception:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="Invalid or unreadable dataset. Please check your file."
        )

    return {
        "message": "Dataset uploaded successfully",
        "dataset_id": dataset_id,
        "filename": file.filename,
        "rows": len(dataframe),
        "columns": len(dataframe.columns),
        "column_names": dataframe.columns.tolist()
    }


@app.get("/api/datasets/{dataset_id}/preview")
def preview_dataset(
    dataset_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0, le=1_000_000),
):
    file_path = find_dataset(dataset_id)
    try:
        dataframe = read_dataset(
            file_path,
            nrows=limit + 1,
            skiprows=range(1, offset + 1),
        )
        has_more = len(dataframe) > limit
        page = dataframe.iloc[:limit]
        rows = json.loads(page.to_json(orient="records", date_format="iso"))
        return {
            "dataset_id": str(uuid.UUID(dataset_id)),
            "columns": page.columns.tolist(),
            "rows": rows,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not preview this dataset.",
        )


@app.get("/api/datasets/{dataset_id}/profile")
def get_dataset_profile(dataset_id: str):
    file_path = find_dataset(dataset_id)
    try:
        df = read_dataset(file_path)
        profile = profile_dataset(df)

        return {
            "dataset_id": str(uuid.UUID(dataset_id)),
            "filename": file_path.name,
            "profile": profile
        }

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not profile this dataset."
        )


@app.get("/api/datasets/{dataset_id}/report")
def download_dataset_report(dataset_id: str):
    file_path = find_dataset(dataset_id)
    try:
        dataframe = read_dataset(file_path)
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dataset": {
                "dataset_id": str(uuid.UUID(dataset_id)),
                "filename": file_path.name,
                "rows": len(dataframe),
                "columns": len(dataframe.columns),
            },
            "profile": profile_dataset(dataframe),
        }
        return JSONResponse(
            content=report,
            headers={
                "Content-Disposition": (
                    f'attachment; filename="dataguard-report-{dataset_id}.json"'
                )
            },
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not generate a report for this dataset.",
        )


@app.get("/api/datasets/{dataset_id}/cleaned")
def download_cleaned_dataset(
    dataset_id: str,
    missing_strategy: Literal["keep", "drop_rows", "fill_median_mode"] = "keep",
    remove_duplicates: bool = False,
):
    file_path = find_dataset(dataset_id)
    try:
        dataframe = read_dataset(file_path)
        (
            cleaned,
            removed_incomplete_rows,
            removed_duplicate_rows,
            filled_values,
        ) = (
            prepare_cleaned_dataset(
                dataframe,
                missing_strategy,
                remove_duplicates,
            )
        )
        headers = {
            "Content-Disposition": (
                f'attachment; filename="dataguard-cleaned-{dataset_id}.csv"'
            ),
            "X-DataGuard-Original-Rows": str(len(dataframe)),
            "X-DataGuard-Exported-Rows": str(len(cleaned)),
            "X-DataGuard-Removed-Incomplete-Rows": str(removed_incomplete_rows),
            "X-DataGuard-Removed-Duplicate-Rows": str(removed_duplicate_rows),
            "X-DataGuard-Filled-Values": str(filled_values),
        }
        return Response(
            content=cleaned.to_csv(index=False, na_rep=""),
            media_type="text/csv",
            headers=headers,
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not create a cleaned export for this dataset.",
        )