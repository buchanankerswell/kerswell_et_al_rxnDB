rxnDB: Mineral Reaction Database
================================

.. container:: .large

    rxnDB collects published high-pressure mineral reactions in one searchable place. Look up an experiment, fit the data, plan your next run.

Quickstart
----------

.. code-block:: bash

    pip install rxnDB
    rxndb

Query the data from your browser or a script:

.. code-block:: bash

    http://127.0.0.1:8000/?query=qz+coe&reaction_type=phase_boundary&selected=hp11-016

The link opens the coesite-quartz boundary with its experimental data and uncertainty. See :doc:`installation` for environment setup and :doc:`usage` for the full walkthrough.

.. toctree::
   :maxdepth: 2
   :caption: Documentation
   :hidden:

   installation
   usage
   api
   autoapi/index
