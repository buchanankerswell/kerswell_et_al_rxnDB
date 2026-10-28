API reference
=============

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

Endpoints
---------

``GET /health`` returns ``{"status": "ok"}``.

``GET /reactions`` lists records. Filters: ``mineral_symbol`` tests set membership, comma-separated (``?mineral_symbol=Qz,Coe``). ``reaction_type`` keeps one type. ``query`` splits on spaces and matches words in any order. It keeps records holding two or more of them, ranked by overlap. Prefix a word with ``-`` to drop holders, and bare identifiers match explicitly.

``GET /reactions/{id}`` fetches one record. 404 means an unknown identifier.

``GET /export`` downloads the filtered records as a ``rxndb-export.json`` attachment. It accepts the ``/reactions`` filters.

``POST /validate`` echoes a record body. 422 names the fault, for example ``legacy symbol 'q': use 'Qz'``.

``POST /fit/boundary`` takes ``{"reaction_identifier": "<id>"}`` and returns the slope in GPa per C, intercept in GPa, their standard errors, the observation count, the method name, and a 20-point line with band half-widths. 404 means an unknown identifier. 422 means a record with fewer than two observations.

``POST /design/next-point`` takes ``{"reaction_identifier": "<id>", "candidate_count": 5}`` plus optional ``temperature_min_celsius``, ``temperature_max_celsius``, ``assumed_temperature_uncertainty_celsius`` (default 10.0), and ``assumed_pressure_uncertainty_gigapascal`` (default 0.05). Each candidate returns a temperature, the predicted pressure, and the expected slope-variance drop, ranked best first.

``GET /`` and ``GET /observations`` serve the human explorer and table (HTML).

Example reads:

.. code-block:: bash

    curl 'http://127.0.0.1:8000/reactions?query=qz%20coe&reaction_type=phase_boundary'
    curl 'http://127.0.0.1:8000/reactions/hp11-016'
    curl 'http://127.0.0.1:8000/export?query=qz%20coe&reaction_type=phase_boundary' -o coe-qz.json
