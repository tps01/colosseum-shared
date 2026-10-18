Getting started
===============

Install the ``colosseum-shared`` wheel into the same virtual environment as
``colosseum-core``. This plugin has **no** TOML config sections: pair it with
equipment, host, messaging, or gui config from those packages.

1. Config
---------

An empty or comment-only file is enough when you only call ``col.shared.*``::

   # config.shared.sim.toml — no [shared.*] tables

2. Procedure + verification
---------------------------

::

   import colosseum as col

   def main() -> None:
       col.shared.wait(duration=0.1)
       col.shared.measure_value(key="uut_version", value="v1.2.3")
       col.shared.regex.verify_match(key="uut_version", pattern=r"v\d+\.\d+\.\d+")
       col.shared.verify.verify_field(key="uut_version", expected_val="v1.2.3")
       col.shared.measure_mark(key="t0")
       col.shared.verify.verify_elapsed(key="budget", mark_key="t0", maximum_s=30.0)

Other common verifies: ``verify_file_exists``, ``verify_new_file``,
``verify_pass`` / ``verify_fail``, ``prompt.comment``. See the package README
table for the full catalog. RF analysis (``col.shared.signal``) is **not** in
this package.

3. Run
------

::

   colosseum run shared_smoke.py -g config.shared.sim.toml

Framework docs: `core hub <https://tps01.github.io/colosseum-core/>`__.
