import json
from io import BytesIO
from pathlib import Path
import uuid

import pandas as pd
from app.services.profiling import profile_dataset
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
        return pd.read_csv(file_path, **options)
    return pd.read_excel(file_path, **options)


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
            dataframe = pd.read_csv(BytesIO(content))
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
):
    file_path = find_dataset(dataset_id)
    try:
        dataframe = read_dataset(file_path, nrows=limit)
        rows = json.loads(dataframe.to_json(orient="records", date_format="iso"))
        return {
            "dataset_id": str(uuid.UUID(dataset_id)),
            "columns": dataframe.columns.tolist(),
            "rows": rows,
            "limit": limit,
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