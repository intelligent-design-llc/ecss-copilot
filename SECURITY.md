# Security Policy

## Supported versions
Only the latest release on the default branch receives fixes while the project is pre-1.0.

## Reporting a vulnerability
Please **do not open a public issue** for security problems.
Use GitHub's private vulnerability reporting instead: **Security → Report a vulnerability** on this repository.
We aim to acknowledge reports within 7 days.

Please include affected version/commit, reproduction steps and impact. Do not include real project data.

## Deployment notes
- The app has **no authentication** and is meant for local or single-user use. It binds to `127.0.0.1` by default. If you expose it on a network (including via Docker), put it behind an authenticating reverse proxy and TLS.
- Uploaded files are processed in memory and are not persisted by the app. Request size is limited to 15 MB.
- When the optional LLM pass is enabled, requirement text is sent to the configured `LLM_BASE_URL`. Use a local model, or a provider whose data-retention terms you have reviewed. **Never process ITAR/EAR-controlled or classified data with this tool.**
- Keep API keys in environment variables or an untracked `.env` file; never commit them.
