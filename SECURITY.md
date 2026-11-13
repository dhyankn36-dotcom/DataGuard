# Security Policy

## Supported versions

Security fixes are applied to the latest version on the default branch.

## Reporting a vulnerability

Please do not publish credentials, private data, or exploitable vulnerability details in a public issue.

Use GitHub's **Security** tab and the private vulnerability reporting option for this repository. Include the affected component, impact, and steps to reproduce. Allow time for investigation and a fix before public disclosure.

## Deployment checklist

- Set strong, unique secrets through the hosting provider's secret manager.
- Use HTTPS and secure cookie settings in production.
- Restrict database and storage access to the application.
- Keep dependencies updated and review automated dependency pull requests.
- Avoid uploading confidential or personal datasets to public demo deployments.
