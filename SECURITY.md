# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email [security@databricks.com](mailto:security@databricks.com) with:

1. A description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Any suggested fixes (optional)

We will acknowledge receipt within 72 hours and provide a timeline for a fix.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest on `main` | Yes |
| Older releases | Best effort |

## Security Best Practices for Contributors

- Never commit secrets, tokens, or credentials — even in tests.
- Use placeholder values (e.g., `1234567890123456`) for workspace IDs in examples.
- All dependencies are scanned via Dependabot; address PRs promptly.
- GitHub secret scanning is enabled on this repository.
