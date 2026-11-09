# Starter fuzz target

`text.py` exposes `check_input(bytes)` for both pytest seed replay and Atheris.
Inputs are bounded to 512 bytes. No external services or devices are used.

Run the checked-in corpus on any supported platform:

```sh
python -m pytest tests/unit/test_fuzz_seeds.py -q
```

For coverage-guided mutation, use an isolated Linux x86_64 Python 3.12 developer
installation (`pip install -r requirements.txt`). Atheris is Apache-2.0 licensed
and a developer dependency only. From the repository root:

```sh
mkdir -p .fuzz-work/corpus .fuzz-work/artifacts
cp tests/fuzz/corpus/* .fuzz-work/corpus/
python tests/fuzz/text.py .fuzz-work/corpus -max_total_time=30 -max_len=512 -timeout=5 -artifact_prefix=.fuzz-work/artifacts/
```

The working corpus can grow; only deliberate seeds belong in `tests/fuzz/corpus`.
Replay a finding by passing its file instead of the corpus directory. Preserve
confirmed bugs as named regression tests. Longer mutation runs are manual;
ordinary pytest/CI replays the checked-in seeds without importing Atheris.

Checks first-number extraction using generated signed/decimal/exponent tokens,
float-list results and rejection against Python conversion, and key/value
semantics including duplicate keys and Unicode line boundaries. Arbitrary regex
patterns and timing guarantees are outside this starter.

## Manual coverage reports

Use an isolated project developer environment with `coverage>=7.6` installed
from `requirements.txt`. Avoid upgrading the shared mutation-testing environment,
which requires an older coverage.py. Atheris is not needed for these reports.

```sh
python tests/fuzz/coverage_report.py
python tests/fuzz/coverage_report.py --corpus .fuzz-work/corpus --output .fuzz-work/coverage/explored
```

The default command replays the tracked corpus plus the empty input and writes
`.coverage`, `coverage.json`, and `html/index.html` under
`.fuzz-work/coverage/text/`. Reports include production line and branch
coverage, exclude the fuzz harness, and print missing lines to the terminal.
The custom corpus command can measure inputs retained by a longer fuzz session.

Reports are manual diagnostics, with no CI job or coverage threshold. Percentages
cover the whole selected production modules, including functions outside this
starter target. A higher percentage alone does not establish correctness.
