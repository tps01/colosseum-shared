# Colosseum Shared

## Documentation

API reference (GitHub Pages): https://tps01.github.io/colosseum-shared/

Framework hub: https://tps01.github.io/colosseum-core/

First-party Colosseum plugin providing `col.shared.*` general utilities:
timed waits, one-off measurements, generic verifications, regex checks, text
parsing helpers, and operator prompts. Protocol clients such as SSH live in
`colosseum-messaging` (`col.messaging.ssh`). RF analysis (`col.shared.signal`)
is not part of this package.

## Install

Download the wheel from [GitHub Releases](https://github.com/tps01/colosseum-shared/releases)
and install it in the same environment as core. Replace `<version>` with
the downloaded filename. For development, use `python -m pip install -e .`.

```bash
python -m pip install "./colosseum_shared-<version>-py3-none-any.whl"
```

This requires `colosseum-core` `>=0.17.0,<0.18` and registers the `shared` namespace
through the `colosseum.plugins` entry point.

## Generic fallbacks

| Need | API |
| --- | --- |
| Sleep | `col.shared.wait(duration=…)` |
| Record a literal | `col.shared.measure_value(key=…, value=…)` |
| Record env var | `col.shared.measure_env(key=…, name=…)` + `verify.verify_env` |
| Wall-clock budget | `measure_mark` + `verify.verify_elapsed` |
| Equal / ±tolerance | `verify.verify_field` |
| Regex on measurement | `regex.verify_match` |
| File exists / contents | `verify.verify_file_*` |
| Intentional PASS/FAIL | `verify.verify_pass` / `verify.verify_fail` |
| Annotate the run | `col.shared.comment(message=…)` |
| Operator input | `prompt.*` (needs interactive stdin / TTY) |
| Parse floats / KV | `col.shared.parsing.*` (undecorated helpers, not evidence) |

File reads assume UTF-8. Prompts block on stdin and may require a TTY on Unix.

## Usage

From this repository root, run the complete, non-interactive example:

```bash
colosseum run examples/portable_checks.py -g examples/configs/config.shared.sim.toml
```

It creates its own file fixtures and demonstrates structured fields, parsing,
regex, file/timing checks and optional trial voting. Expected exit: 0, with one
intentional optional FAIL retained in the results. See
[portable evidence workflows](https://tps01.github.io/colosseum-shared/guides/evidence_workflows.html).

```python
import colosseum as col

def main():
    col.shared.measure_value(key="version", value="v1.2.3")
    col.shared.regex.verify_match(key="version", pattern=r"^v\d+\.\d+\.\d+$")
    col.shared.verify.verify_field(key="version", expected_val="v1.2.3")

if __name__ == "__main__":
    col.config.load_config("examples/configs/config.shared.sim.toml")
    main()
    col.endex()
```

Operator prompts are a separate interactive example:
`colosseum run examples/operator_prompt.py` (requires stdin/TTY; excluded from CI).
Shared field/regex checks choose the latest measurement with the key across all
domains. Use distinct keys for distinct facts. Timing marks are local to the
current timing session; file checks require actual accessible files.

## Expected artifacts

Normal CLI runs write `summary.json`, `summary.txt`, `execution.sqlite`, and
`debug.log` under the run output directory. Reports are opt-in: add
`--report wats` to the run command to write `wats_<datetime>_<script>.json`,
or `--report junit` for `junit.xml`. Loading `metadata.yaml` enriches an
enabled report; it does not enable reporting. See the
[core reporting guide](https://tps01.github.io/colosseum-core/guides/output_artifacts.html).

## Develop

```bash
pip install -e ../colosseum-core
pip install -e .
pytest
ruff check .
mypy
```

### Inclusive numeric bounds (0.5.0+)

```python
col.shared.measure_value(key="jitter_ps", value=2.0)
col.shared.verify.verify_field(key="jitter_ps", minimum=0.0, maximum=5.0)
col.shared.measure_value(key="harmonic_dbc", value=-60.0)
col.shared.verify.verify_field(key="harmonic_dbc", maximum=-40.0)
```

Use either `expected_val` / `tolerance` or `minimum` / `maximum`. Bounds are
inclusive, must be finite and ordered, and reject nonnumeric/non-finite evidence.
Missing comparison arguments produce ERROR rather than an implicit verdict.
