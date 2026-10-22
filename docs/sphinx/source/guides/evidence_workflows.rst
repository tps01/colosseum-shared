Portable evidence checks
========================

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

For numeric limits, use inclusive ``minimum`` and/or ``maximum`` (Shared 0.5.0+)::

   col.shared.measure_value(key="jitter_ps", value=2.0)
   col.shared.verify.verify_field(key="jitter_ps", minimum=0.0, maximum=5.0)
   col.shared.measure_value(key="harmonic_dbc", value=-60.0)
   col.shared.verify.verify_field(key="harmonic_dbc", maximum=-40.0)

Do not combine bounds with ``expected_val`` / ``tolerance``. Invalid or non-finite
bounds/evidence produce ERROR. Boolean expectations require actual Boolean
evidence; integers and strings do not stand in for ``True`` / ``False``.

Shared 0.6.0 requires numeric expectations to use finite evidence, a finite
expectation, and a finite nonnegative tolerance. Integers, including integer
strings, compare exactly when the other side is an integer.

``verify_m_of_n`` checks the latest ``n`` prior verification results, excluding
optional results unless ``include_optional=True``. From Shared 0.6.0, ``m`` and
``n`` must be integers with ``0 < m <= n``; any other window is ERROR. It cannot
undo required failures already recorded. For a trial-voting policy, mark each trial optional
and make the final m-of-n check required. ``verify_all_passed`` excludes optional
results by default and examines every earlier required result in the run.

Time and replay
---------------

``measure_mark`` stores a performance-counter value. Use ``verify_elapsed`` only
within the current timing session. ``verify_time_delta`` instead compares the
stored measurement timestamps, so it can work with imported rows. Filesystem
checks need the actual files, not just their prior measurement rows. The portable
example recreates temporary files when run; it is not a file-replay fixture.

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
