import json
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Literal
import uuid

import pandas as pd
from app.auth import (
    SESSION_LIFETIME_SECONDS,
    authenticate_request,
    connect_database,
    create_user,
    hash_password,
    hash_session_token,
    initialize_database as initialize_auth_database,
    require_admin,
    verify_password,
)
from app.services.profiling import profile_dataset
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "datasets"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
DATABASE_PATH = Path(
    os.getenv("DATAGUARD_DATABASE_PATH", str(BASE_DIR / "dataguard.sqlite3"))
).resolve()

MAX_FILE_SIZE = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
SESSION_COOKIE = "dataguard_session"


def cookie_secure_setting() -> bool:
    value = os.getenv("DATAGUARD_COOKIE_SECURE", "false").strip().lower()
    if value not in {"true", "false"}:
        raise ValueError("DATAGUARD_COOKIE_SECURE must be true or false.")
    return value == "true"


COOKIE_SECURE = cookie_secure_setting()
DUMMY_PASSWORD_HASH = hash_password("DataGuard invalid account password")


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(max_length=1024)


class CreateUserRequest(BaseModel):
    email: str = Field(
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    password: str = Field(min_length=12, max_length=1024)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(max_length=1024)
    new_password: str = Field(min_length=12, max_length=1024)


def initialize_database() -> None:
    initialize_auth_database(DATABASE_PATH)


def current_user(request: Request) -> dict:
    return authenticate_request(request, DATABASE_PATH)


def create_session(user_id: str) -> tuple[str, int]:
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    expires_at = now + SESSION_LIFETIME_SECONDS
    with connect_database(DATABASE_PATH) as connection:
        connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        connection.execute(
            """
            INSERT INTO sessions (token_hash, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (hash_session_token(token), user_id, expires_at, now),
        )
    return token, expires_at

@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="DataGuard API",
    description="Intelligent Data Quality Monitoring Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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


@app.post("/api/auth/login")
def login(payload: LoginRequest, response: Response):
    normalized_email = payload.email.strip().lower()
    with connect_database(DATABASE_PATH) as connection:
        user = connection.execute(
            "SELECT user_id, email, password_hash, role FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()

    password_hash = user["password_hash"] if user else DUMMY_PASSWORD_HASH
    password_valid = verify_password(payload.password, password_hash)
    if user is None or not password_valid:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token, _ = create_session(user["user_id"])
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_LIFETIME_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return {
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "role": user["role"],
        }
    }


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with connect_database(DATABASE_PATH) as connection:
            connection.execute(
                "DELETE FROM sessions WHERE token_hash = ?",
                (hash_session_token(token),),
            )
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )
    return {"message": "Logged out."}


@app.get("/api/auth/me")
def get_current_user(user: dict = Depends(current_user)):
    return {"user": user}


@app.put("/api/auth/password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    user: dict = Depends(current_user),
):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")
    token_hash = hash_session_token(token)

    with connect_database(DATABASE_PATH) as connection:
        connection.execute("BEGIN IMMEDIATE")
        account = connection.execute(
            "SELECT password_hash FROM users WHERE user_id = ?",
            (user["user_id"],),
        ).fetchone()
        if account is None or not verify_password(
            payload.current_password, account["password_hash"]
        ):
            raise HTTPException(status_code=400, detail="Current password is incorrect.")
        if verify_password(payload.new_password, account["password_hash"]):
            raise HTTPException(
                status_code=400,
                detail="Choose a new password different from your current password.",
            )

        connection.execute(
            "UPDATE users SET password_hash = ? WHERE user_id = ?",
            (hash_password(payload.new_password), user["user_id"]),
        )
        connection.execute(
            "DELETE FROM sessions WHERE user_id = ? AND token_hash != ?",
            (user["user_id"], token_hash),
        )

    return {"message": "Password changed. Other active sessions have been signed out."}


@app.post("/api/admin/users", status_code=201)
def add_user(
    payload: CreateUserRequest,
    admin: dict = Depends(current_user),
):
    require_admin(admin)
    try:
        user = create_user(
            DATABASE_PATH, payload.email, payload.password, role="user"
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="An account with that email exists.")
    return {"user": user}


@app.get("/api/admin/users")
def list_users(admin: dict = Depends(current_user)):
    require_admin(admin)
    with connect_database(DATABASE_PATH) as connection:
        rows = connection.execute(
            """
            SELECT user_id, email, role, created_at
            FROM users
            ORDER BY created_at, email COLLATE NOCASE
            """
        ).fetchall()
    return {
        "users": [
            {
                "user_id": row["user_id"],
                "email": row["email"],
                "role": row["role"],
                "created_at": datetime.fromtimestamp(
                    row["created_at"], timezone.utc
                ).isoformat(),
            }
            for row in rows
        ]
    }


def find_dataset(dataset_id: str, user_id: str) -> Path:
    try:
        normalized_id = str(uuid.UUID(dataset_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dataset ID.")

    with connect_database(DATABASE_PATH) as connection:
        dataset = connection.execute(
            "SELECT extension FROM datasets WHERE dataset_id = ? AND user_id = ?",
            (normalized_id, user_id),
        ).fetchone()
    if dataset is None or dataset["extension"] not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    candidate = UPLOAD_DIR / f"{normalized_id}{dataset['extension']}"
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return candidate


def original_dataset_filename(dataset_id: str, user_id: str) -> str:
    with connect_database(DATABASE_PATH) as connection:
        dataset = connection.execute(
            """
            SELECT original_filename FROM datasets
            WHERE dataset_id = ? AND user_id = ?
            """,
            (str(uuid.UUID(dataset_id)), user_id),
        ).fetchone()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return dataset["original_filename"]


def read_dataset(file_path: Path, **options) -> pd.DataFrame:
    if file_path.suffix.lower() == ".csv":
        return pd.read_csv(file_path, **options)
    return pd.read_excel(file_path, **options)


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
def list_datasets(user: dict = Depends(current_user)):
    with connect_database(DATABASE_PATH) as connection:
        rows = connection.execute(
            """
            SELECT dataset_id, original_filename, extension, size_bytes
            FROM datasets
            WHERE user_id = ?
            ORDER BY original_filename COLLATE NOCASE
            """,
            (user["user_id"],),
        ).fetchall()
    datasets = [
        {
            "dataset_id": row["dataset_id"],
            "filename": row["original_filename"],
            "size_bytes": row["size_bytes"],
            "file_type": row["extension"][1:].upper(),
        }
        for row in rows
    ]
    return {"datasets": datasets}


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id: str, user: dict = Depends(current_user)):
    file_path = find_dataset(dataset_id, user["user_id"])
    file_path.unlink()
    with connect_database(DATABASE_PATH) as connection:
        connection.execute(
            "DELETE FROM datasets WHERE dataset_id = ? AND user_id = ?",
            (str(uuid.UUID(dataset_id)), user["user_id"]),
        )
    return {
        "message": "Dataset deleted successfully",
        "dataset_id": str(uuid.UUID(dataset_id)),
    }


@app.post("/api/datasets/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    user: dict = Depends(current_user),
):
    original_filename = Path((file.filename or "").replace("\\", "/")).name
    extension = Path(original_filename).suffix.lower()

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

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid or unreadable dataset. Please check your file."
        )

    destination.write_bytes(content)
    try:
        with connect_database(DATABASE_PATH) as connection:
            connection.execute(
                """
                INSERT INTO datasets (
                    dataset_id, user_id, original_filename, extension,
                    size_bytes, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset_id,
                    user["user_id"],
                    original_filename,
                    extension,
                    len(content),
                    int(time.time()),
                ),
            )
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    return {
        "message": "Dataset uploaded successfully",
        "dataset_id": dataset_id,
        "filename": original_filename,
        "rows": len(dataframe),
        "columns": len(dataframe.columns),
        "column_names": dataframe.columns.tolist()
    }


@app.get("/api/datasets/{dataset_id}/preview")
def preview_dataset(
    dataset_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    user: dict = Depends(current_user),
):
    file_path = find_dataset(dataset_id, user["user_id"])
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
def get_dataset_profile(dataset_id: str, user: dict = Depends(current_user)):
    file_path = find_dataset(dataset_id, user["user_id"])
    try:
        df = read_dataset(file_path)
        profile = profile_dataset(df)

        return {
            "dataset_id": str(uuid.UUID(dataset_id)),
            "filename": original_dataset_filename(dataset_id, user["user_id"]),
            "profile": profile
        }

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not profile this dataset."
        )


@app.get("/api/datasets/{dataset_id}/report")
def download_dataset_report(dataset_id: str, user: dict = Depends(current_user)):
    file_path = find_dataset(dataset_id, user["user_id"])
    try:
        dataframe = read_dataset(file_path)
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dataset": {
                "dataset_id": str(uuid.UUID(dataset_id)),
                "filename": original_dataset_filename(dataset_id, user["user_id"]),
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
    user: dict = Depends(current_user),
):
    file_path = find_dataset(dataset_id, user["user_id"])
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