# Colosseum Shared

First-party Colosseum plugin providing `col.shared.*` general utilities
(regex verification and text parsing). Protocol clients such as SSH live in
`colosseum-messaging` (`col.messaging.ssh`).

## Install

```bash
pip install colosseum-shared
```

This requires `colosseum-core` 0.15.x and registers the `shared` namespace through the
`colosseum.plugins` entry point.

## Usage

```python
import colosseum as col

col.config.load_config("examples/configs/bench.shared.sim.toml")
# After any measurement stored under key="uut_version":
col.shared.regex.verify_match(key="uut_version", pattern=r"v\d+\.\d+\.\d+")
col.endex()
```

SSH remote exec is `col.messaging.ssh.measure_stdout` from `colosseum-messaging`.

## Develop

```bash
pip install -e ../colosseum-core
pip install -e ".[test,static]"
pytest
ruff check .
mypy
```
