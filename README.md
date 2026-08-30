# Colosseum Shared

First-party Colosseum plugin providing `col.shared.*` general utilities
(generic verifications, regex verification, text parsing, and operator prompts).
Protocol clients such as SSH live in `colosseum-messaging`
(`col.messaging.ssh`).

## Install

```bash
pip install colosseum-shared
```

This requires `colosseum-core` 0.16.1+ and registers the `shared` namespace
through the
`colosseum.plugins` entry point.

## Usage

```python
import colosseum as col

col.config.load_config("examples/configs/config.shared.sim.toml")
# After any measurement stored under key="uut_version":
col.shared.regex.verify_match(key="uut_version", pattern=r"v\d+\.\d+\.\d+")
# Generic field check (any domain, latest row for key):
col.shared.verify.verify_field(key="uut_version", expected_val="v1.2.3")
col.shared.verify.verify_measurement_exists(key="uut_version")
col.shared.verify.verify_file_exists(key="profile", path="profile.json")
col.shared.verify.verify_time_delta(
    key="ready",
    other_key="power_on",
    expected_s=5.0,
    tolerance_s=0.5,
)
# Meta verifications (aggregate prior checks in this run):
col.shared.verify.verify_all_passed(key="summary")
col.shared.verify.verify_m_of_n(key="summary", m=2, n=3)
# Operator prompts (blocking stdin):
col.shared.prompt.comment(message="Attach probe to J5")
col.shared.prompt.prompt(message="Confirm DUT power LED is green")
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
