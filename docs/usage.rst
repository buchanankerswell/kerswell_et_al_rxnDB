Usage
=====

Start the server
----------------

After :doc:`installation`, start the server with:

.. code-block:: bash

    rxndb

The command launches the app on http://127.0.0.1:8000/.

Open the interface
------------------

Visit http://127.0.0.1:8000/. The page shows a search box, a reaction-type dropdown, a reaction list, a dependency-free SVG pressure-temperature plot, and an observation table. Press ``/`` to focus search. ``Download JSON`` exports the current filter set.

Worked example: coesite-quartz
------------------------------

Paste this address into the browser:

.. code-block:: bash

    http://127.0.0.1:8000/?query=qz+coe&reaction_type=phase_boundary&selected=hp11-016

The page lists two quartz-coesite candidates and plots ``hp11-016``, the Bose & Ganguly (1995) coesite to quartz boundary with eight observations from 500 to 1200 C.

To reach the same view by hand:

1. Open http://127.0.0.1:8000/
2. Type ``qz coe`` in search
3. Select ``phase_boundary`` from the dropdown
4. Click ``hp11-016: Coe + Qz`` in the list

The API is the URL itself:

* ``query=qz+coe`` matches ``Qz`` and ``Coe`` against the database. Matching ignores case and splits on spaces, so ``qz coe`` and ``coe qz`` find the same records; ``+`` decodes to a space.
* ``reaction_type=phase_boundary`` keeps only phase boundaries. Other values are ``calibration``, ``melting_curve``, and ``triple_point``.
* ``selected=hp11-016`` highlights that reaction and draws its fit.

Share URL to reproduce results
------------------------------

The app rewrites the URL on every keystroke and selection, so copy the URL to share exactly what you see. An empty filter shows the full database.

Search syntax
-------------

The ``query`` box splits on spaces and matches words in any order. One word
matches directly; several words keep only records holding a combination (two
or more) of them, with the most overlapping records first. Tokens naming a
reaction identifier always match that record explicitly. Prefix a word with
``-`` to drop records holding it.

Examples:

* ``qz`` finds all quartz-bearing records.
* ``qz coe`` and ``coe qz`` find the same quartz-coesite records.
* ``coe sti qz`` finds records pairing any two of those phases, such as
  ``coe sti``, ``coe qz``, and ``coe sti qz`` combinations, without the
  records holding only one of them.
* ``jimmy-032 hp11-133`` shows exactly those two records.
* ``coe sti qz -h2o`` keeps those pairings but drops any holding ``H2O``.
* ``bose`` finds records citing Bose & Ganguly.
* ``hp11-016`` jumps to one record.

The ``mineral_symbol`` API parameter differs: it tests set membership and accepts comma-separated symbols (``?mineral_symbol=Qz,Coe``), while ``query`` tests words in any order.

Download matching records
-------------------------

``Download JSON`` calls ``GET /export`` with the current filters and saves ``rxndb-export.json``. The file holds full records in the same schema as the API.

Call the API
------------

Browsers and scripts share these endpoints:

=========================== ====================================================
Endpoint                    Purpose
=========================== ====================================================
``GET /health``             Liveness check, returns ``{"status": "ok"}``.
``GET /reactions``          List records; accepts ``query``, ``mineral_symbol``, ``reaction_type``.
``GET /reactions/{id}``     Fetch one record by identifier; 404 when unknown.
``GET /export``             Download filtered records as a JSON attachment.
``POST /validate``          Validate a record body; 422 names the fault.
``POST /fit/boundary``      Fit a line to a record's observations.
``POST /design/next-point`` Rank candidate temperatures by expected slope-variance drop.
``GET /``                   The search page.
=========================== ====================================================

The worked example above corresponds to:

.. code-block:: bash

    curl 'http://127.0.0.1:8000/reactions?query=qz%20coe&reaction_type=phase_boundary'
    curl 'http://127.0.0.1:8000/reactions/hp11-016'
    curl 'http://127.0.0.1:8000/export?query=qz%20coe&reaction_type=phase_boundary' -o coe-qz.json

Validate a candidate record before upload:

.. code-block:: bash

    curl -X POST http://127.0.0.1:8000/validate \
        -H 'Content-Type: application/json' \
        -d @my-reaction.json

Unknown mineral symbols fail with a suggestion, for example ``legacy symbol 'q': use 'Qz'``. IMA Warr (2021) symbols pass. The remaining registry entries are provisional single-symbol forms awaiting verification.

Fit a boundary
--------------

.. code-block:: bash

    curl -X POST http://127.0.0.1:8000/fit/boundary \
        -H 'Content-Type: application/json' \
        -d '{"reaction_identifier": "hp11-016"}'

The response reports slope in GPa per C, intercept in GPa, standard errors, observation count, method name, and a 20-point line with band half-widths. The method is iterated weighted least squares with temperature-error propagation. Records with fewer than two observations return 422.

Pick the next experiment
------------------------

.. code-block:: bash

    curl -X POST http://127.0.0.1:8000/design/next-point \
        -H 'Content-Type: application/json' \
        -d '{"reaction_identifier": "hp11-016", "candidate_count": 5}'

Each candidate returns a temperature, the predicted pressure, and the expected slope-variance drop. The plot stars the top five candidate experiments and scales each star by its variance drop. Optional fields narrow the grid (``temperature_min_celsius``, ``temperature_max_celsius``) or restate the assumed point errors (``assumed_temperature_uncertainty_celsius``, ``assumed_pressure_uncertainty_gigapascal``).

Data and symbols
----------------

Each file under ``rxnDB/data/`` holds one reaction. Curves store polynomial coefficients with valid ranges. JSON Schema is at ``rxnDB/schema/reaction.json``.

Troubleshooting
---------------

* The page loads but the plot is empty. The filters exclude everything; clear search and set the type dropdown to ``all types``. With more than 200 matches the plot shows the first 200 and says so; the list and table still show everything.
* ``/fit/boundary`` returns 422. The record holds fewer than two observations; pick a record with a point set.
* ``/validate`` rejects a symbol. Check ``rxnDB/registry.json`` for the canonical form and fix the ``mineral_symbol``, ``mineral_name``, and ``chemical_formula`` triple together.
* Port 8000 is busy. Start the app on another port: ``python -m uvicorn rxnDB.api:app --port 8001``.
