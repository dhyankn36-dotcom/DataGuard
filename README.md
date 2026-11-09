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
Dataset files and Python virtual environments are excluded from Git.

## API

- `GET /api/datasets` — list datasets stored by the API.
- `POST /api/datasets/upload` — upload a CSV or XLSX file (`file` form field).
- `DELETE /api/datasets/{dataset_id}` — permanently delete an uploaded dataset.
- `GET /api/datasets/{dataset_id}/profile` — retrieve the quality profile.
- `GET /api/datasets/{dataset_id}/report` — download a JSON quality report.
- `GET /api/datasets/{dataset_id}/preview?limit=100` — preview up to 1,000 rows.
- `GET /health` — check API health.

## Tests

Run the backend tests from `backend/`:

```powershell
python -m pytest -q
```
