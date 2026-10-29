Small evidence recipes
======================

Install core and Shared in the same environment. Save each script below in a
standalone directory with a comment-only **config.toml**. Run with
``colosseum run numeric.py -g config.toml`` (substitute the chosen script).
All three demonstrations require no external service or DUT. They write normal
core evidence and summaries; the file examples create temporary fixtures and
remove them after verification.

Verify a numeric measurement: numeric.py
----------------------------------------

::

   import colosseum as col

   def main() -> None:
       col.shared.measure_value(key="rail_v", value=3.3)
       col.shared.verify.verify_field(key="rail_v", minimum=3.2, maximum=3.4)

Expected: one measurement, one required PASS, exit 0. This records a literal,
not a physical measurement. Use distinct keys: Shared field/regex checks select
the latest match across all domains and commands.

Wait for a log message: log_check.py
------------------------------------

::

   from pathlib import Path
   from tempfile import TemporaryDirectory
   import colosseum as col

   def main() -> None:
       with TemporaryDirectory() as directory:
           log = Path(directory) / "device.log"
           log.write_text("device ready\n", encoding="utf-8")
           match = col.shared.verify.wait_for_log_line(str(log), pattern=r"device ready", timeout_s=1.0)
           col.shared.measure_value(key="ready_line", value=match)
           col.shared.verify.verify_field(key="ready_line", expected_val="device ready")

Expected: PASS and exit 0. In a live procedure, trigger the producer before
polling. The helper returns ``None`` at timeout; recording and verifying its
return makes the timeout affect acceptance. It is an undecorated helper,
so it still polls in dry-run or replay mode.

Verify that a new file appeared: new_file.py
--------------------------------------------

::

   from pathlib import Path
   from tempfile import TemporaryDirectory
   import colosseum as col

   def main() -> None:
       with TemporaryDirectory() as directory:
           before = col.shared.verify.snapshot_files(directory, pattern="*.txt")
           (Path(directory) / "result.txt").write_text("done", encoding="utf-8")
           col.shared.verify.verify_new_file(key="created", directory=directory, before=before, pattern="*.txt", timeout_s=1.0)

Expected: one required PASS and exit 0. Capture ``before`` before the action
under test. A new path establishes appearance, not that writing is complete.
See :doc:`/api/verify` for snapshots, waits, and file verifiers; see
:doc:`evidence_workflows` for timing, replay, and the full demonstration.
