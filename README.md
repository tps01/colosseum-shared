# Colosseum Shared

First-party Colosseum plugin providing `col.shared.*` (SSH, regex, parsing).

## Install

```bash
pip install colosseum-core
pip install -e ".[ssh,test]"
```

Requires `colosseum-core` 0.15.x. Registers the `shared` namespace via the `colosseum.plugins` entry point.

## Usage

```python
import colosseum as col

col.config.load_config("examples/configs/bench.shared.sim.toml")
col.shared.ssh.measure_stdout(ssh_id=1, command="uname -a", key="uname")
col.endex()
```

## Develop

```bash
pip install -e ../colosseum-core
pip install -e ".[ssh,test,static]"
pytest
```
