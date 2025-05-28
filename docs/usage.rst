Usage Guide
===========

After installing rxnDB, you can launch the Shiny app directly from the command line:

.. code-block:: bash

    # Activate conda environment
    conda activate rxnDB

    # Launch app
    rxndb

For more advanced usage, you can use the following options:

.. code-block:: bash

    # Activate conda environment
    conda activate rxnDB

    # rxndb --host 0.0.0.0   (Make accessible from other machines)
    # rxndb --port 8080      (Run on a specific port)
    # rxndb --launch-browser (Open browser automatically)
    # rxndb --reload         (Auto-reload when files change)

    # Default command
    rxndb --host 127.0.0.1 --port 8000 --launch-browser --reload
