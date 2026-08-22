# NOTICE

**SecFlow AI — AI-Powered Security Service Automation Platform**

Copyright (c) 2026 SecFlow AI Contributors. Licensed under the MIT License
(see `LICENSE`).

This repository contains original code written for SecFlow AI. It integrates
with the following **third-party open-source projects** as *external
components* (deployed separately, never vendored into this repository). Each
project retains its own license; SecFlow AI is not a derivative work of them.

| Component | Purpose in SecFlow | Upstream | License | Pinned version |
|-----------|--------------------|----------|---------|----------------|
| Wazuh | SIEM / host security event source | https://github.com/wazuh/wazuh-docker | GPL-2.0 | v4.14.7 (single-node) |
| Nuclei | Vulnerability / exposure scanning engine | https://github.com/projectdiscovery/nuclei | MIT | latest stable (image `projectdiscovery/nuclei`) |
| MISP | Threat intelligence sharing platform | https://github.com/MISP/misp-docker | AGPL-3.0 | latest stable |

Third-party components are cloned **at install time** by `deploy/` scripts from
their official pinned releases — see `docs/licensing.md` for details. SecFlow
AI communicates with them only through public APIs / containers.

## Additional third-party notices

SecFlow AI is built on widely-used open-source libraries including, but not
limited to: FastAPI, SQLAlchemy, Pydantic, Celery, React, Ant Design, ECharts,
Vite. All such dependencies retain their own licenses; dependency manifests
(`pyproject.toml`, `package.json`) are the authoritative source.

## Trademarks

Wazuh, Nuclei, MISP and other names are trademarks of their respective owners.
Use of these names does not imply endorsement.
