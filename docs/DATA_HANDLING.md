# Dataset Lifecycle and Safe Handling

## Upload

DataGuard accepts CSV and XLSX files within the documented upload-size limit. Uploaded files are stored under generated UUID-based names in the datasets directory. Use non-sensitive sample files when exploring the application.

## Inspection and profiling

Preview, summary, and profiling operations analyze the uploaded dataset. Quality metrics such as missing values, duplicate rows, and numeric statistics describe the data; they do not prove that a dataset is accurate, unbiased, or suitable for a particular use.

## Cleaning and export

Cleaning options create a transformed export. The original uploaded source is intended to remain unchanged. Review the selected missing-value strategy and duplicate-row setting before downloading or sharing an export.

CSV exports can be opened by spreadsheet applications. Be cautious when sharing files externally and inspect the output for confidential columns or records.

## Deletion and backups

Deleting a dataset is a permanent action through the application. The SQLite database and datasets directory may contain user information and should be protected together. Backups should be stored securely and tested before being relied upon.

## Safe development practices

- Prefer synthetic datasets in tests and bug reports.
- Never commit real datasets, database files, session cookies, or credentials.
- Remove personal or confidential values from screenshots and logs.
- Confirm dataset ownership and authorization when changing API routes.
