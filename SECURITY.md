# Security Policy

## Reporting a vulnerability

If you find a security issue in a skill in this repo — or in a skill published to the Sophon
Marketplace — please report it privately. **Do not** open a public issue for security problems.

- Email **security@buildersoft.io** with a description, affected skill(s), and reproduction steps.
- Or use GitHub's **private vulnerability reporting** ("Report a vulnerability" under the Security
  tab) if enabled on this repo.

We aim to acknowledge reports within a few business days and will coordinate a fix and disclosure
timeline with you.

## Scope

Skills run in a sandbox and declare their required `permissions` (network hosts, filesystem paths,
resource limits) and credential scopes in `manifest.json`. Reports we especially want to hear about:

- A skill requesting or exercising more access than its manifest declares.
- Credential/secret handling flaws (leakage, over-broad scopes, logging secrets).
- Input handling that enables SSRF, path traversal, injection, or sandbox escape.
- A manifest that misrepresents a tool's `riskLevel`.

The Marketplace also performs its own validation and moderation on upload; this policy covers the
skill **sources** in this repository.
