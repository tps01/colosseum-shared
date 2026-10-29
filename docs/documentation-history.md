# Historical feature notes

Current behavior is documented in the evidence workflow and API reference.

### Wall time and operator checks (0.7.0+)

`measure_mark` / `verify_elapsed` stay on the monotonic perf counter.
`measure_wall_time` records UTC ISO-8601 wall time.
`verify_wall_time_delta` compares that value with another measurement or with
an `expected` timestamp string.

Prompts accept `timeout_s` and return after recording ERROR instead of hanging.
`prompt_choice` records a closed set of answers as a normal verification.
`verify.wait_for_log_line` polls a file until a regex matches.
`run_process` runs a local program and records stdout plus the exit code.

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

### Finite tolerances and exact integers (0.6.0+)

Numeric `expected_val` checks require finite evidence, a finite expectation,
and a finite nonnegative tolerance. Integers, including integer strings, compare
exactly when the other side is an integer.
