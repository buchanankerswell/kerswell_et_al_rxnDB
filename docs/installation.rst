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

    # Checkout develop branch
    git checkout develop

    # Create conda environment and install rxnDB locally in editable mode
    # including optional development and documentation dependencies
    make create_conda_env