"""Interactive-only operator confirmation; requires stdin/TTY.

Run from the repository root with ``colosseum run examples/operator_prompt.py``.
Type PASS when asked to produce a passing run. Do not use in unattended CI.
"""

from pathlib import Path

import colosseum as col


def main() -> None:
    col.config.load_config(str(Path(__file__).with_name("configs") / "config.shared.sim.toml"))
    col.shared.prompt.comment(message="Attach the probe to J5.")
    col.shared.prompt.prompt_measurement(message="Enter serial number: ", key="serial")
    col.shared.prompt.prompt_exit(message="Type PASS to confirm: ", key="ack", expected="PASS")


if __name__ == "__main__":
    main()
    col.endex()
