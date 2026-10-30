Portable evidence checks
========================

Choose a verification
---------------------

.. list-table::
   :header-rows: 1

   * - Task
     - Callable
   * - Compare a number or structured field
     - ``col.shared.verify.verify_field``
   * - Find text in recorded evidence
     - ``col.shared.regex.verify_match``
   * - Check a recorded environment value
     - ``col.shared.measure_env`` then ``col.shared.verify.verify_env``
   * - Check an accessible file
     - ``verify_file_exists`` / ``verify_file_contents``
   * - Check an action created a file
     - ``snapshot_files`` before the action, then ``verify_new_file``
   * - Wait for log text
     - ``wait_for_log_line`` then record and verify the match
   * - Record an explicit verdict
     - ``verify_pass`` / ``verify_fail``
   * - Check elapsed time
     - ``measure_mark`` / ``verify_elapsed``
   * - Ask an operator
     - ``col.shared.prompt.*`` (interactive input required)

See :doc:`recipes` for small complete examples, :doc:`/api/verify` for exact
verification arguments, and :doc:`/api/regex` for regex modes. Field/regex
lookups choose the latest key across domains; keep separate facts under
separate keys.

Complete demonstration
----------------------

From the repository root::

   colosseum run examples/portable_checks.py -g examples/configs/config.shared.sim.toml

The script creates its own temporary UTF-8 fixture files, needs no services or
interactive input, and exits 0. Normal core logs, SQLite and summaries persist;
temporary file fixtures are deleted. A deliberate optional FAIL is retained in
the results so its effect on the exit status is visible.

.. literalinclude:: ../../../../examples/portable_checks.py
   :language: python

``measure_value`` records literal strings, numbers or structured values;
``measure_env`` records a string and raises ``KeyError`` for an unset variable.
Parsing functions return Python values without recording evidence. Wrap their
result in ``measure_value`` when later verification must use it.

Field and regex verifiers choose the most recent measurement with that ``key``
across **all domains and command names**. Use distinct keys for distinct facts;
reusing a key in another plugin can change which value a shared verifier checks.
``field=`` selects a dictionary/JSON field rather than the entire value.

For numeric limits, use inclusive ``minimum`` and/or ``maximum``::

   col.shared.measure_value(key="jitter_ps", value=2.0)
   col.shared.verify.verify_field(key="jitter_ps", minimum=0.0, maximum=5.0)
   col.shared.measure_value(key="harmonic_dbc", value=-60.0)
   col.shared.verify.verify_field(key="harmonic_dbc", maximum=-40.0)

Do not combine bounds with ``expected_val`` / ``tolerance``. Invalid or non-finite
bounds/evidence produce ERROR. Boolean expectations require actual Boolean
evidence; integers and strings do not stand in for ``True`` / ``False``.

Numeric comparisons require numeric expectations to use finite evidence, a finite
expectation, and a finite nonnegative tolerance. Integers, including integer
strings, compare exactly when the other side is an integer.

``verify_m_of_n`` checks the latest ``n`` prior verification results, excluding
optional results unless ``include_optional=True``. ``m`` and ``n`` must be integers with ``0 < m <= n``; any other window is ERROR. It cannot
undo required failures already recorded. For a trial-voting policy, mark each trial optional
and make the final m-of-n check required. ``verify_all_passed`` excludes optional
results by default and examines every earlier required result in the run.

Time and replay
---------------

``measure_mark`` stores ``time.perf_counter()``, a monotonic elapsed mark for
this process. ``verify_elapsed`` subtracts a later perf-counter reading from
that mark. The mark does not move backward when the wall clock steps, and it
is meaningless in another run or on another machine. Use it only inside the
current timing session.

``verify_time_delta`` uses the UTC timestamps core writes on evidence rows, so
it can replay imported rows. A clock step can shrink or stretch that delta.

``measure_wall_time`` stores the bench UTC time as an ISO-8601 string in the
measurement value. ``verify_wall_time_delta`` subtracts two such strings (a
second measurement, or an ``expected`` literal such as a timestamp copied from
a product log) and passes when the absolute difference is within
``tolerance_s``. That pair is how a log line meets the bench clock. It is not
an elapsed budget.

Filesystem checks need the actual files, not just their prior measurement rows.
The portable example recreates temporary files when run; it is not a file-replay
fixture.

Field/regex comparisons against stored values are suitable for verification-only
replay. Core's runtime execution guide includes a plugin-free numeric/text replay
procedure. ``verify_env`` compares the prior ``measure_env`` row, so that pair
can replay a recorded environment snapshot without reading the current value.

Interactive operators
---------------------

Run ``colosseum run examples/operator_prompt.py`` in a terminal. It asks for a
serial number and the text PASS. This example requires interactive stdin/TTY and
is deliberately excluded from unattended documentation checks. Prompts are
procedure operations; a prior DB does not substitute for current operator input.
