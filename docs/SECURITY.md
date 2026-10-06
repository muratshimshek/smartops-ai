# Security

## Current controls

- Secrets load from environment variables or the ignored `.env` file.
- Administrative routes require `X-Admin-Token`.
- Allowed roots are resolved to canonical paths.
- Traversal outside an allowed root is rejected.
- Directory indexing does not follow symbolic links.
- Discovered files are never executed.
- File downloads resolve an indexed identifier and revalidate its allowed root.
- Write proposals cannot modify files before approval.
- Approval fails if the target changed after the proposal was created.
- Existing files receive a backup before replacement.
- File operations produce audit records.
- Provider keys are not included in API responses or logs.

## Data excluded from version control

The ignore rules exclude local environment files, databases, virtual environments, caches, logs, build artifacts, generated package metadata, local test documents, and SmartOps backup directories.

Before publishing, run a secret scanner against the complete Git history. Removing a secret from the latest file does not remove it from earlier commits.

## Known limitations

- Document search has no end-user authentication or per-user ACL filtering.
- The administrator token is a local-development control, not enterprise identity.
- SQLite is not intended for concurrent production workloads.
- Provider credentials are stored in plaintext in `.env`.
- The native directory picker is available only to a loopback client on the server desktop.
- OCR, archive inspection, malware scanning, and encrypted-document extraction are not implemented.

Do not expose this version to the public internet or use it for sensitive multi-user data.

## Reporting

Do not include credentials, private documents, personal paths, or production data in a vulnerability report. Provide a minimal reproduction using synthetic data.

