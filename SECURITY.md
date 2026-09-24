# Security policy — laya-ultrafast

Report vulnerabilities privately: open a GitHub issue titled
`[SECURITY]` with minimal detail, or contact the maintainer via
the profile email. Do not open a public issue with exploit detail.

Scope: `ultrafast/`, `backends/`, `demos/`, `scripts/`. The local
Laya model server (`:8770`) is the operator's own machine — keep
credentials server-side, `.env` ignored, tests never call paid APIs.

Secrets: never commit API keys, tokens, or `.env`. CI runs offline
(ruff + pytest + node check); release uploads need `PYPI_API_TOKEN`.
