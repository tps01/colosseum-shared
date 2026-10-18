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

``verify_m_of_n`` checks the latest ``n`` prior verification results, excluding
optional results unless ``include_optional=True``. It cannot undo required
failures already recorded. For a trial-voting policy, mark each trial optional
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
