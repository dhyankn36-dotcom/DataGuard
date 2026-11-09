from app.services.profiling import profile_dataset
from io import BytesIO
from pathlib import Path
import uuid

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "datasets"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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


@app.get("/")
def root():
    return {
        "message": "Welcome to DataGuard API",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


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


@app.get("/api/datasets/{dataset_id}/profile")
def get_dataset_profile(dataset_id: str):
    try:
        uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid dataset ID."
        )

    matching_files = list(UPLOAD_DIR.glob(f"{dataset_id}.*"))

    if not matching_files:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found."
        )

    file_path = matching_files[0]

    try:
        if file_path.suffix.lower() == ".csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        profile = profile_dataset(df)

        return {
            "dataset_id": dataset_id,
            "filename": file_path.name,
            "profile": profile
        }

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not profile this dataset."
        )