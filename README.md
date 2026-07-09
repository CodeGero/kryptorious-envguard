# envguard

> Validate, generate, and secure your .env files. Catch secrets before they ship.

[![PyPI](https://img.shields.io/pypi/v/kryptorious-envguard)](https://pypi.org/project/kryptorious-envguard/) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Part of the [Kryptorious developer toolkit](https://kryptorious.gumroad.com/l/jbvet) — 31 open-source tools, one $9 lifetime license.

## Install

```bash
pip install kryptorious-envguard
```

## Quickstart

```bash
printf 'DB_PASSWORD=changeme\n' > .env
envguard check --path . --strict
# -> exit 1 (placeholder value detected)
```

## Commands

| Command | Description |
|---------|-------------|
| `envguard check --path .` | Check .env files for empty values, placeholders, and hardcoded secrets. |
| `envguard check --path . --strict` | Fail (exit 1) on any warning — use as a CI gate. |
| `envguard generate .env --output .env.example` | Produce a template with values stripped, keys kept. |



## License

MIT — free for personal and commercial use. The $9 lifetime license adds DevFlow Premium (multi-environment CI/CD, approval gates, infrastructure-as-code). Get it at [kryptorious.gumroad.com/l/jbvet](https://kryptorious.gumroad.com/l/jbvet).
