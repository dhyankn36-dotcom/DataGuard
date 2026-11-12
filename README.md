# DataGuard

<div align="center">

### A lightweight data quality workspace for CSV and Excel datasets

Upload a dataset, inspect its quality, explore records, and export a cleaned copy without changing the original file.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pandas](https://img.shields.io/badge/Data-Pandas-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Pytest](https://img.shields.io/badge/Tests-Pytest-0A9EDC?logo=pytest&logoColor=white)](https://pytest.org/)

</div>

---

## Overview

DataGuard is a data quality monitoring application for CSV and XLSX files. It provides a simple workspace for uploading datasets, reviewing their contents, profiling data quality, and exporting transformed copies.

The FastAPI application serves the web interface and exposes endpoints for dataset management, previews, quality profiles, JSON reports, and cleaned CSV exports.

## Features

- **CSV and XLSX uploads:** Accept supported tabular files up to 20 MB.
- **Dataset management:** List uploaded datasets and delete a selected dataset.
- **Data preview:** Inspect records using paginated requests.
- **Preview-page exports:** Download the currently displayed (and searched) preview page as a CSV.
- **Quality profiling:** Review missing values, duplicate records, numeric statistics, and potential outliers through the profiling service.
- **JSON reports:** Generate a downloadable report with dataset metadata and its quality profile.
- **Shareable summaries:** Copy a concise quality summary, including the score, missing-value rate, and duplicate count, to the clipboard.
- **Column quality exports:** Download the currently filtered and sorted columns, including missingness, uniqueness, duplicate counts, and numeric statistics, as a spreadsheet-friendly CSV.
- **Cleaned exports:** Download a transformed CSV using configurable missing-value and duplicate-row options.
- **Original-file preservation:** Cleaning operations work on a DataFrame copy; the uploaded source file is not modified.
- **Health endpoint:** Check whether the API is responding.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend application logic |
| FastAPI | HTTP API and application server |
| Pandas | Dataset loading, profiling, and transformation |
| NumPy | Numeric data operations |
| OpenPyXL | XLSX file reading |
| Uvicorn | ASGI development server |
| Pytest | Backend testing |

## Architecture

```text
             USER
              |
              v
       DATASET WEB UI
              |
              v
         FASTAPI APP
              |
       +------+------+----------------+
       |             |                |
       v             v                v
   UPLOAD /       PROFILING        EXPORTS
   MANAGEMENT     SERVICE          / REPORTS
       |             |                |
       +-------------+----------------+
                     |
                     v
                PANDAS DATAFRAME
                     |
                     v
              DATASETS DIRECTORY
               (CSV / XLSX files)
```

Uploaded files are stored in the repository-level `datasets/` directory using generated UUID-based filenames. The API returns dataset IDs for subsequent operations.

## Local Setup

### Prerequisites

- Python 3.11 or newer
- Git

### 1. Clone the repository

```powershell
git clone https://github.com/dhyankn36-dotcom/DataGuard.git
cd DataGuard
```

### 2. Create a virtual environment

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Start the application

Run from the `backend/` directory:

```powershell
python -m uvicorn main:app --reload
```

Open the application at [http://127.0.0.1:8000](http://127.0.0.1:8000).

Interactive API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Create the first administrator in a separate terminal before signing in:

```powershell
cd backend
python create_admin.py admin@example.com
```

The command prompts for a password of at least 12 characters. Administrators
can create regular user accounts with `POST /api/admin/users` (also available
through `/docs` after signing in). Public self-registration is disabled.

Sessions use expiring, HTTP-only cookies. For an HTTPS deployment, set
`DATAGUARD_COOKIE_SECURE=true` before starting the API. The default is suitable
for local HTTP development only. Dataset records are private to the account
that uploaded them. The SQLite database is stored at
`dataguard.sqlite3` in the repository root by default; set
`DATAGUARD_DATABASE_PATH` to use a different location. Uploaded CSV and XLSX
files are limited to 20 MB and stored in `datasets/`.

Files already present in `datasets/` are not imported into user accounts and
are not deleted automatically. Back up or remove them deliberately before
starting a fresh authenticated workspace. Dataset files, the database, and
Python virtual environments are excluded from Git.

Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health).

## API Reference

Authentication uses expiring HTTP-only cookies. Dataset endpoints require a
signed-in user; admins can manage accounts.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/login` | Sign in and create a browser session |
| `POST` | `/api/auth/logout` | Revoke the current session |
| `GET` | `/api/auth/me` | Retrieve the signed-in account |
| `PUT` | `/api/auth/password` | Change password and revoke other active sessions |
| `POST` | `/api/admin/users` | Admin-only user account creation |
| `GET` | `/api/admin/users` | Admin-only account directory (no password data) |
| `GET` | `/api/datasets` | List the signed-in user's datasets |
| `POST` | `/api/datasets/upload` | Upload a CSV or XLSX file using the `file` form field |
| `PATCH` | `/api/datasets/{dataset_id}` | Rename an owned dataset without changing its source file |
| `DELETE` | `/api/datasets/{dataset_id}` | Permanently delete an owned dataset |
| `GET` | `/api/datasets/{dataset_id}/preview` | Retrieve a paginated preview of an owned dataset |
| `GET` | `/api/datasets/{dataset_id}/summary` | Retrieve a concise overview of row, column, and data quality counts |
| `GET` | `/api/datasets/{dataset_id}/profile` | Retrieve the quality profile of an owned dataset |
| `GET` | `/api/datasets/{dataset_id}/report` | Download a JSON quality report for an owned dataset |
| `GET` | `/api/datasets/{dataset_id}/cleaned` | Download a cleaned CSV export of an owned dataset |
| `GET` | `/health` | Check API health |

### Upload constraints

- Supported extensions: `.csv` and `.xlsx`
- Maximum upload size: 20 MB
- Empty or unreadable datasets are rejected.
- Dataset identifiers are UUIDs.

### Preview pagination

The preview endpoint accepts:

- `limit`: number of records to return (1–1,000; default 100)
- `offset`: number of records to skip (default 0)
- `search`: optional, case-insensitive literal text matched across all columns
  (maximum 200 characters); when present, `total_rows` reports the number of
  matching rows.

The web preview lets you choose 25, 50, 100, 250, or 500 rows per page.

Example:

```text
GET /api/datasets/{dataset_id}/preview?limit=100&offset=0
```

### Cleaned CSV export

The cleaned export endpoint accepts two query parameters:

| Parameter | Options | Behavior |
|---|---|---|
| `missing_strategy` | `keep` | Preserve missing values (default) |
| `missing_strategy` | `drop_rows` | Remove rows containing missing values |
| `missing_strategy` | `fill_median_mode` | Fill numeric columns with their median and other columns with their most frequent value |
| `remove_duplicates` | `true` / `false` | Optionally remove duplicate rows |

Example:

```text
GET /api/datasets/{dataset_id}/cleaned?missing_strategy=fill_median_mode&remove_duplicates=true
```

The response is a CSV download and includes `X-DataGuard-*` headers with
original/exported row counts and the number of removed or filled values. The
original uploaded dataset remains unchanged.

## Tests

Run backend tests from the `backend/` directory:

```powershell
python -m pytest -q
```

## Data Storage and Safety

- Uploaded files are stored in `datasets/` using generated UUID filenames.
- Dataset files and Python virtual environments should remain excluded from version control.
- The delete endpoint permanently removes the selected uploaded dataset.
- Cleaning and export operations do not overwrite the source dataset.
- Do not upload sensitive or confidential data unless your environment and data-handling requirements permit it.

## Potential Improvements

- More detailed downloadable profiling visualizations.
- Dataset comparison across versions.
- Configurable validation rules and quality thresholds.
- Role management and account lifecycle controls.

## Author

**Dhyan K N**

[GitHub Profile](https://github.com/dhyankn36-dotcom) · [DataGuard Repository](https://github.com/dhyankn36-dotcom/DataGuard)

---

<div align="center">

Built with Python, FastAPI, and Pandas.

</div>
