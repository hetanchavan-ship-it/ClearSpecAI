# Security Policy

## Supported Versions

ClearSpec AI currently supports the latest release and the current `main`
branch.

| Version | Supported |
| --- | --- |
| Latest release | Yes |
| `main` branch | Yes |
| Older releases | No |

## Reporting a Vulnerability

Please do not report security vulnerabilities through public GitHub issues,
discussions, pull requests, or social media.

Use GitHub's private vulnerability reporting feature:

1. Open the repository's **Security** page.
2. Open **Advisories**.
3. Select **Report a vulnerability**.
4. Provide a clear description of the issue and steps to reproduce it.

Include the following information when possible:

- The affected component or endpoint
- Reproduction steps
- Expected and actual behaviour
- Potential security impact
- Relevant logs, screenshots, or proof-of-concept details
- Suggested remediation, when known

Do not include active credentials, API keys, access tokens, private user data,
or other secrets in the report.

## Response Process

The maintainer will aim to:

- Acknowledge the report within 3 business days
- Perform an initial assessment within 14 days
- Provide progress updates when investigation takes longer
- Coordinate disclosure after a fix or mitigation is available

Resolution time will depend on the severity, reproducibility, and complexity of
the vulnerability.

## Responsible Disclosure

Please allow reasonable time for investigation and remediation before publicly
disclosing a vulnerability.

Avoid accessing, modifying, deleting, or downloading data that does not belong
to you. Do not perform testing that disrupts the hosted application or its
underlying services.

## Scope

Security reports may include issues involving:

- Authentication or authorization bypasses
- Exposure of API keys, tokens, or environment variables
- Cross-user access to saved project history
- Malicious file-upload behaviour
- Injection vulnerabilities
- Dependency vulnerabilities affecting ClearSpec AI
- Unsafe handling of model-generated output
- Deployment or configuration weaknesses

General feature requests, ordinary bugs, and documentation corrections should
be submitted through regular GitHub issues.
