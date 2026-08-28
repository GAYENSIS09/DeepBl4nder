# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within DeepBl4nder, please send an email to the project maintainer via GitHub. All security vulnerabilities will be promptly addressed.

Please include the following information in your report:

- Type of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Security Measures

- Generated code is validated via AST analysis before execution
- Path traversal prevention on artifact downloads
- PBKDF2 password hashing with per-user salt
- JWT with refresh token rotation
- Rate limiting on authentication endpoints
- `.env` files excluded from version control
- Non-root Docker containers

## Scope

This security policy applies to the code in this repository. It does not cover:
- Third-party dependencies (report upstream)
- Deployed instances managed by users
- The Blender or Unreal Engine software itself
