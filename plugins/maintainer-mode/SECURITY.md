# Security policy

Report suspected vulnerabilities privately to the repository owner before opening a public issue.

Maintainer Mode deliberately avoids storing raw command output or environment variables. Command arguments are retained with best-effort secret redaction, so callers should still avoid placing credentials directly on a command line.

The receipt digest is an integrity check, not a digital signature or hostile-author defense. Security reports should not assume it establishes who executed a command.
