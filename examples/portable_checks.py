"""Self-contained shared evidence, parsing, regex, file and timing checks.

From this repository root::

    colosseum run examples/portable_checks.py -g examples/configs/config.shared.sim.toml

No services, DUT, interactive input, or hardware. Fixture files live in a
temporary directory and are removed afterward. Expected exit: 0; the deliberate
optional FAIL remains visible in execution.sqlite and the summaries.
"""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

import colosseum as col


def main() -> None:
    col.config.load_config(str(Path(__file__).with_name("configs") / "config.shared.sim.toml"))
    col.shared.measure_value(key="version", value="v1.2.3")
    col.shared.regex.verify_match(key="version", pattern=r"^v\d+\.\d+\.\d+$")
    # Parsing returns data; measure_value explicitly records it as evidence.
    voltage = col.shared.parsing.parse_float("rail=3.31 V")
    col.shared.measure_value(key="rail", value={"voltage": voltage})
    col.shared.verify.verify_field(key="rail", field="voltage", expected_val=3.3, tolerance=0.05)
    os.environ["COLOSSEUM_EXAMPLE_REVISION"] = "fixture-1"
    col.shared.measure_env(key="revision", name="COLOSSEUM_EXAMPLE_REVISION")
    col.shared.verify.verify_field(key="revision", expected_val="fixture-1")
    col.shared.measure_mark(key="start")
    col.shared.wait(duration="10ms")
    col.shared.verify.verify_elapsed(key="budget", mark_key="start", maximum_s=30.0)
    col.shared.measure_value(key="finished", value="done")
    col.shared.verify.verify_time_delta(
        key="finished", other_key="start", expected_s=0.0, tolerance_s=30.0,
    )
    with TemporaryDirectory(prefix="colosseum-shared-") as folder:
        fixture = Path(folder) / "device.log"
        fixture.write_text("READY v1.2.3\n", encoding="utf-8")
        col.shared.verify.verify_file_exists(key="log", path=str(fixture))
        col.shared.verify.verify_file_contents(
            key="ready", path=str(fixture), pattern=r"READY", count=1,
        )
        before = col.shared.verify.snapshot_files(folder, pattern="*.txt")
        (Path(folder) / "capture.txt").write_text("capture complete\n", encoding="utf-8")
        col.shared.verify.verify_new_file(
            key="capture", directory=folder, before=before, pattern="*.txt", timeout_s=1.0,
        )
    # m-of-n cannot erase earlier required failures. Mark trial outcomes optional.
    col.shared.verify.verify_pass(key="trial1", optional=True)
    col.shared.verify.verify_fail(key="trial2", optional=True, message="deliberate demonstration")
    col.shared.verify.verify_pass(key="trial3", optional=True)
    col.shared.verify.verify_m_of_n(key="trials", m=2, n=3, include_optional=True)
    col.shared.verify.verify_all_passed(key="required_checks")


if __name__ == "__main__":
    main()
    col.endex()
