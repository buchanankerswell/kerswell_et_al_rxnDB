Usage Guide
===========

After installing rxnDB, launch the API directly from the command line:

.. code-block:: bash

    # Activate conda environment
    conda activate rxnDB

    # Launch server (UI at http://127.0.0.1:8000/)
    rxndb

The same JSON serves browsers and agents:

.. code-block:: bash

    curl 'http://127.0.0.1:8000/reactions?mineral_symbol=Qz' | head -c 300
    curl -X POST http://127.0.0.1:8000/fit/boundary \
        -H 'Content-Type: application/json' \
        -d '{"reaction_identifier": "hp11-001"}'
