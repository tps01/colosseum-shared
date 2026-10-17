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

```bash
pip install colosseum-shared
```

This requires `colosseum-core` 0.16.4+ and registers the `shared` namespace
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
| Operator input | `prompt.*` (needs interactive stdin / TTY) |
| Parse floats / KV | `parsing.text.*` (undecorated helpers, not evidence) |

File reads assume UTF-8. Prompts block on stdin and may require a TTY on Unix.

## Usage

```python
import colosseum as col

col.config.load_config("examples/configs/config.shared.sim.toml")
col.shared.wait(duration=2)
col.shared.wait(duration="500ms", progress_bar=True)
col.shared.measure_value(key="uut_version", value="v1.2.3")
col.shared.regex.verify_match(key="uut_version", pattern=r"v\d+\.\d+\.\d+")
col.shared.verify.verify_field(key="uut_version", expected_val="v1.2.3")
col.shared.verify.verify_measurement_exists(key="uut_version")
col.shared.measure_mark(key="t0")
# ... work ...
col.shared.verify.verify_elapsed(key="budget", mark_key="t0", maximum_s=30.0)
col.shared.verify.verify_file_exists(key="profile", path="profile.json")
col.shared.verify.verify_file_contents(
    key="log_has_error",
    path="uut.log",
    pattern=r"ERROR",
    count=1,
)
before = col.shared.verify.snapshot_files("captures", pattern="*_screenshot.*")
# ... trigger the product ...
col.shared.verify.verify_new_file(
    key="shot",
    directory="captures",
    before=before,
    pattern="*_screenshot.*",
    timeout_s=15.0,
)
col.shared.verify.verify_time_delta(
    key="ready",
    other_key="power_on",
    expected_s=5.0,
    tolerance_s=0.5,
)
col.shared.verify.verify_all_passed(key="summary")
col.shared.verify.verify_m_of_n(key="summary", m=2, n=3)
col.shared.prompt.comment(message="Attach probe to J5")
col.shared.prompt.prompt(message="Confirm the dialog is visible")
col.shared.prompt.prompt_measurement(message="Enter serial number: ", key="serial")
col.shared.prompt.prompt_exit(message="Type PASS to continue: ", key="ack", expected="PASS")
col.endex()
```

SSH remote exec is `col.messaging.ssh.measure_stdout` from
`colosseum-messaging`.

## Expected artifacts

Normal CLI runs write `summary.json`, `summary.txt`, `execution.sqlite`, and
`debug.log` under the run output directory. When metadata is loaded (see
`examples/configs/metadata.yaml`), core also emits a WATS-format
`wats_<datetime>_<script>.json` report alongside those files.

## Develop

```bash
pip install -e ../colosseum-core
pip install -e .
pytest
ruff check .
mypy
```
