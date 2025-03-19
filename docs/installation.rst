Installation Guide
==================

To install with Conda (recommended):

.. code-block:: bash

    # Create conda environment 
    conda create -n rxnDB python=3.13 pip

    # Activate conda environment
    conda activate rxnDB

    # Install rxnDB
    pip install rxnDB

If you want to install the development version locally for testing in "editable" mode:

.. code-block:: bash

    # Clone repo
    git clone https://github.com/buchanankerswell/kerswell_et_al_rxnDB.git
    cd kerswell_et_al_rxnDB

    # Create conda environment
    make create_conda_env
    conda activate rxnDB

    # Uninstall rxnDB and reinstall locally in editable mode (incl. optional dependencies)
    pip uninstall rxnDB
    pip install -e ".[dev,docs]"