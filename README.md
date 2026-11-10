# DataGuard

DataGuard is a lightweight data quality workspace. Upload a CSV or XLSX file to
review missing values, duplicate records, numeric statistics, potential
outliers, and a preview of the source rows.
The column-quality table shows both completeness and the exact missing-value
count for each column.

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
`backend/dataguard.sqlite3` by default; set `DATAGUARD_DATABASE_PATH` to use a
different location. Uploaded CSV and XLSX files are limited to 20 MB and
stored in `datasets/`.

Files already present in `datasets/` are not imported into user accounts and
are not deleted automatically. Back up or remove them deliberately before
starting a fresh authenticated workspace. Dataset files, the database, and
Python virtual environments are excluded from Git.

## API

- `POST /api/auth/login` — sign in and create a browser session.
- `POST /api/auth/logout` — revoke the current session.
- `GET /api/auth/me` — retrieve the signed-in account.
- `PUT /api/auth/password` — change the signed-in user's password; verifies the current password and signs out other active sessions.
- `POST /api/admin/users` — administrator-only creation of a regular user account.
- `GET /api/admin/users` — administrator-only account directory (passwords and hashes are never returned).
- `GET /api/datasets` — list the signed-in user's datasets.
- `POST /api/datasets/upload` — upload a CSV or XLSX file (`file` form field) to the signed-in user's workspace.
- `DELETE /api/datasets/{dataset_id}` — permanently delete an owned dataset.
- `GET /api/datasets/{dataset_id}/profile` — retrieve the quality profile of an owned dataset.
- `GET /api/datasets/{dataset_id}/report` — download an owned dataset's JSON quality report.
- `GET /api/datasets/{dataset_id}/cleaned` — download a transformed CSV with optional `missing_strategy=drop_rows|fill_median_mode` and `remove_duplicates=true`. Median values fill numeric columns, most-common values fill other columns, and entirely empty columns stay empty. The response includes row/value counts in `X-DataGuard-*` headers; the source file is never modified.
- `GET /api/datasets/{dataset_id}/preview?limit=100&offset=0` — paginate through an owned dataset's rows (up to 1,000 per request).
- `GET /health` — check API health.

## Tests

Run the backend tests from `backend/`:

```powershell
python -m pytest -q
```
