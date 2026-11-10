# DataGuard

DataGuard is a lightweight data quality workspace. Upload a CSV or XLSX file to
review missing values, duplicate records, numeric statistics, potential
outliers, and a preview of the source rows.

## Run locally

Requirements: Python 3.11 or newer.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The API documentation is
available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

CSV and XLSX uploads are limited to 20 MB and are stored in `datasets/`.
CSV files are read as UTF-8 (including UTF-8 with a BOM), with Windows-1252 as
a fallback for legacy Windows exports. Dataset files and Python virtual
environments are excluded from Git.

## API

- `GET /api/datasets` — list datasets stored by the API.
- `POST /api/datasets/upload` — upload a CSV or XLSX file (`file` form field).
- `DELETE /api/datasets/{dataset_id}` — permanently delete an uploaded dataset.
- `GET /api/datasets/{dataset_id}/profile` — retrieve the quality profile.
- `GET /api/datasets/{dataset_id}/report` — download a JSON quality report.
- `GET /api/datasets/{dataset_id}/cleaned` — download a transformed CSV with optional `missing_strategy=drop_rows|fill_median_mode` and `remove_duplicates=true`. Median values fill numeric columns, most-common values fill other columns, and entirely empty columns stay empty. The response includes row/value counts in `X-DataGuard-*` headers; the source file is never modified.
- `GET /api/datasets/{dataset_id}/preview?limit=100&offset=0` — paginate through rows (up to 1,000 per request).
- `GET /health` — check API health.

## Tests

Run the backend tests from `backend/`:

```powershell
python -m pytest -q
```
