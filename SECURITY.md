# Security Policy

## Supported versions

Security fixes are accepted for the latest version on the default branch.

## Reporting a vulnerability

Do not publish uploaded datasets, session cookies, passwords, database files, or exploit details in a public issue. Use the repository's private vulnerability reporting option in GitHub's Security tab. Include the affected endpoint, impact, and safe reproduction steps using synthetic data.

## Application-specific precautions

- Treat CSV/XLSX uploads, generated reports, and exports as potentially sensitive.
- Use synthetic or anonymized datasets for development and bug reports.
- Protect the SQLite database and datasets directory with appropriate filesystem permissions.
- Verify dataset ownership and authorization when changing API routes.
- Review upload validation and export behavior when modifying file-handling code.

## Deployment checklist

Use HTTPS, secure cookie settings, protected persistent storage, and a deliberate backup and retention policy. Allow reasonable time to investigate reports before public disclosure.
