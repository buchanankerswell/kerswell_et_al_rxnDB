Agent API
=========

For autonomous agents. Humans: start with :doc:`usage`.

Base URL defaults to ``http://127.0.0.1:8000/``. Reads are ``GET`` with query strings. Writes are ``POST`` with ``Content-Type: application/json``. Records are served from the bundled corpus and nothing is stored server-side. Errors return the cause in the response body. 404 means an unknown identifier. 422 means an invalid payload.

Data model
----------

Minimal valid record (validates as-is against ``POST /validate``):

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

Field rules: ``reaction_identifier`` matches ``^[A-Za-z0-9][A-Za-z0-9._-]*$``. ``reaction_type`` is one of ``phase_boundary``, ``calibration``, ``melting_curve``, ``triple_point``. ``reactants`` and ``products`` are non-empty. Each phase names a canonical ``mineral_symbol`` plus its exact ``mineral_name`` and ``chemical_formula`` triple from ``rxnDB/registry.json`` and a positive ``coefficient``. At least one of ``observations`` or ``interpreted_boundaries`` must be present. ``observations`` carry temperatures in C and pressures in GPa with non-negative uncertainties and a correlation in [-1, 1]. ``source.authors`` is non-empty. Full schema: ``rxnDB/schema/reaction.json``.

Data files: each file under ``rxnDB/data/`` holds one reaction. Curves store polynomial coefficients with valid ranges. JSON Schema is at ``rxnDB/schema/reaction.json``.

Endpoints
---------

.. list-table::
   :header-rows: 1

   * - Endpoint
     - Contract
   * - ``GET /health``
     - Returns ``{"status": "ok"}``.
   * - ``GET /reactions``
     - Lists records with ``mineral_symbol`` (comma-separated), ``reaction_type``, and ``query`` filters (see below).
   * - ``GET /reactions/{id}``
     - Fetches one record. 404 means an unknown identifier.
   * - ``GET /export``
     - Downloads the filtered records as a ``rxndb-export.json`` attachment; accepts the ``/reactions`` filters.
   * - ``POST /validate``
     - Echoes a record body. 422 names the fault (see below).
   * - ``POST /fit/boundary``
     - Fits a phase boundary for ``{"reaction_identifier": "<id>"}``. 404 means an unknown identifier; 422 means fewer than two observations.
   * - ``POST /design/next-point``
     - Ranks candidate next measurements for a reaction (see below).
   * - ``GET /``
     - Human reactions explorer (HTML).
   * - ``GET /observations``
     - Human observations table (HTML).

``GET /reactions`` filters: ``mineral_symbol`` tests set membership and accepts comma-separated symbols (``?mineral_symbol=Qz,Coe``), while ``query`` tests words in any order. ``reaction_type`` keeps one type. ``query`` splits on spaces and matches words in any order. It keeps records holding two or more of them, ranked by overlap. Prefix a word with ``-`` to drop holders, and bare identifiers match explicitly.

``GET /export`` holds the full records behind the current filters.

``POST /validate`` 422s name the fault, for example ``legacy symbol 'q': use 'Qz'``. When a symbol is rejected, check ``rxnDB/registry.json`` for the canonical form and fix the ``mineral_symbol``, ``mineral_name``, and ``chemical_formula`` triple together.

``POST /fit/boundary`` returns the slope in GPa per C, intercept in GPa, their standard errors, the observation count, the method name, and a 20-point line with band half-widths. 422 means the record holds fewer than two observations; pick a record that has observations.

``POST /design/next-point`` takes ``{"reaction_identifier": "<id>", "candidate_count": 5}`` plus optional ``temperature_min_celsius``, ``temperature_max_celsius``, ``assumed_temperature_uncertainty_celsius`` (default 10.0), and ``assumed_pressure_uncertainty_gigapascal`` (default 0.05). Each candidate returns a temperature, the predicted pressure, and the expected slope-variance drop, ranked best first.

Example reads:

.. code-block:: bash

    curl 'http://127.0.0.1:8000/reactions?query=qz%20coe&reaction_type=phase_boundary'
    curl 'http://127.0.0.1:8000/reactions/hp11-016'
    curl 'http://127.0.0.1:8000/export?query=qz%20coe&reaction_type=phase_boundary' -o coe-qz.json
