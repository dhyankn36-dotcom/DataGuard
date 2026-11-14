# DataGuard Release Checklist

Use this checklist before publishing or deploying a new DataGuard version.

## Upload and access

- [ ] Upload sample CSV and XLSX files within the configured size limit.
- [ ] Verify that empty, malformed, and unsupported files are rejected clearly.
- [ ] Confirm dataset listings and operations are scoped to the signed-in account.
- [ ] Test session expiry, logout, and password-change behavior.
- [ ] Verify that administrative account operations require an admin session.

## Data quality and exports

- [ ] Compare preview and profile results against a small known dataset.
- [ ] Check missing-value, duplicate-row, and numeric-statistic calculations.
- [ ] Verify pagination and search boundaries.
- [ ] Test each documented missing-value strategy.
- [ ] Confirm duplicate removal is optional and the uploaded source remains unchanged.
- [ ] Inspect CSV output for confidential columns and spreadsheet formula handling.
- [ ] Compare quality scores shown in the UI and JSON report.

## Storage and privacy

- [ ] Confirm dataset files and the SQLite database are not tracked by Git.
- [ ] Verify upload directory permissions in the deployment environment.
- [ ] Test backup and restore procedures with disposable data.
- [ ] Use synthetic data in screenshots, bug reports, and tests.

## Quality checks

- [ ] Run `python -m pytest -q` from `backend/`.
- [ ] Review the GitHub Actions result.
- [ ] Check dependency changes and installation instructions.
- [ ] Update API documentation and README for changed endpoints or parameters.

## Publish

- [ ] Review the final diff and configuration changes.
- [ ] Document any migration or operational steps.
- [ ] Publish release notes with known limitations.
