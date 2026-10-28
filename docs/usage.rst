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

Visit http://127.0.0.1:8000/. A search box and a reaction-type dropdown sit above two tabs. ``Reactions`` pairs the reaction list with a plain SVG phase diagram. ``Observations`` lists every matching observation with its reaction. Press ``/`` to jump to search from either tab. ``Download JSON`` exports the current filter set.

Data format
-----------

Each reaction is one JSON record: named phases on each side of the change, at least one observation or published curve, and a source. A minimal record with two observations validates as-is:

.. code-block:: json

    {
      "reaction_identifier": "example-001",
      "reaction_type": "phase_boundary",
      "reactants": [
        {"mineral_symbol": "Coe", "mineral_name": "coesite", "chemical_formula": "SiO2", "coefficient": 1.0}
      ],
      "products": [
        {"mineral_symbol": "Qz", "mineral_name": "quartz", "chemical_formula": "SiO2", "coefficient": 1.0}
      ],
      "observations": [
        {"temperature_celsius": 500, "temperature_uncertainty_celsius": 10, "pressure_gigapascal": 2.7, "pressure_uncertainty_gigapascal": 0.05},
        {"temperature_celsius": 800, "temperature_uncertainty_celsius": 10, "pressure_gigapascal": 3.0, "pressure_uncertainty_gigapascal": 0.05}
      ],
      "source": {"authors": ["Bose", "Ganguly"], "year": 1995, "short_citation": "Bose & Ganguly, 1995"}
    }

Each file under ``rxnDB/data/`` holds one such record. The exact format lives in :doc:`api`.

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

* ``query=qz+coe`` matches ``Qz`` and ``Coe`` against the database. Matching ignores case and splits on spaces, so ``qz coe`` and ``coe qz`` find the same records. ``+`` decodes to a space.
* ``reaction_type=phase_boundary`` keeps only phase boundaries. Other values are ``calibration``, ``melting_curve``, and ``triple_point``.
* ``selected=hp11-016`` highlights that reaction and draws its fit.

Share URL to reproduce results
------------------------------

The app rewrites the URL on every keystroke and selection. Copy the URL to share exactly what you see. An empty filter shows the full database. The tab lives in the path: ``/`` holds the reactions explorer and ``/observations`` holds the table, with the same ``query``, ``reaction_type``, and ``selected`` parameters on both. Switching tabs slides the underline, crossfades the view, and adds a history entry, so the back and forward buttons move between tabs.

Tabs
----

Both tabs share one search box and one filter set:

* ``Reactions`` (``/``): ranked reaction list plus the phase diagram. Click a reaction to fit it. Hovering a point lights up its whole reaction. Ctrl-click (or Cmd-click) a point to select that reaction and center it in the list. Scroll to zoom around the cursor, drag to pan, double-click (or ``Reset view``) to return to the full filter set.
* ``Observations`` (``/observations``): one row per observation with ``reaction``, ``phases`` (symbols plus long-form names), ``T``, ``P``, ``type``, and ``source`` columns, in ranked reaction order.

The same ``/`` address from the worked example opens the table here:

.. code-block:: bash

    http://127.0.0.1:8000/observations?query=qz+coe&reaction_type=phase_boundary

Search syntax
-------------

The ``query`` box splits on spaces and matches words in any order. One word
matches directly. Several words keep only records holding a combination (two
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

Call the API
------------

Scripts and agents can call the same URLs the browser uses. The full technical reference lives in :doc:`api`.

Troubleshooting
---------------

* The page loads but the plot is empty. The filters exclude everything. Clear search and set the type dropdown to ``all types``. The plot draws every match, so a very broad filter renders hundreds of series at once.
* Port 8000 is busy. Start the app on another port: ``python -m uvicorn rxnDB.api:app --port 8001``.
