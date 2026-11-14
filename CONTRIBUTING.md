# Contributing to DataGuard

Thanks for helping improve DataGuard. Contributions should protect uploaded source datasets and make data-quality results predictable.

## Getting started

1. Fork the repository and clone your fork.
2. Create a focused branch from `main`, for example `feature/profile-export` or `fix/xlsx-validation`.
3. Follow the local setup instructions in [README.md](README.md).
4. Make a focused change and add or update tests where appropriate.

## Development guidelines

- Preserve the original uploaded dataset; transformations and exports should operate on copies.
- Keep dataset ownership checks on every dataset-specific operation.
- Validate file type, size, and parsed content before accepting uploads.
- Treat uploaded file contents as untrusted input.
- Keep authentication, session, and administrator authorization behavior intact.
- Avoid exposing local filesystem paths, secrets, or other users' dataset metadata in API responses.
- Never commit uploaded datasets, SQLite databases, environment files, credentials, or virtual environments.
- Update API documentation when request parameters or response formats change.

## Run backend tests

From the backend directory, activate your virtual environment, install the requirements, and run:

```bash
python -m pytest -q
```

Include regression tests for bug fixes, especially around file parsing, access control, and cleaning/export behavior.

## Pull requests

Explain the user problem, the change, and its effect on existing data or API behavior. Include test results and any manual verification performed. For UI changes, add screenshots when useful. Keep each pull request focused.

## Reporting issues

Provide a small reproducible example where possible, expected and actual behavior, and sanitized error output. Do not attach confidential datasets, personal information, or credentials.
