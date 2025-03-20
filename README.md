# rxnDB: a mineral reaction database

📚 See the [documentation](https://kerswell-et-al-rxndb.readthedocs.io/en/latest/) for details.

## Prerequisite software

This project is written in [python](https://www.python.org). For most users, I recommend installing the [miniforge](https://github.com/conda-forge/miniforge) python distribution. This distributions includes a minimal installation of python and the package manager [conda](https://docs.conda.io/en/latest/), which is required to build the necessary python environment for this software.

For macOS users, miniforge can be installed with [homebrew](https://brew.sh):

```bash
brew install miniforge
```

## Installation Guide

To install with Conda (recommended):

``` bash
# Create conda environment
conda create -n rxnDB python=3.13 pip

# Activate conda environment
conda activate rxnDB

# Install rxnDB
pip install rxnDB
```

If you want to install the development version for local testing in "editable" mode:

``` bash
# Clone repo
git clone https://github.com/buchanankerswell/kerswell_et_al_rxnDB.git
cd kerswell_et_al_rxnDB

# Checkout develop branch
git checkout develop

# Create conda environment and install rxnDB locally in editable mode
# including optional development and documentation dependencies
make create_conda_env
```

## Usage Guide

After installing rxnDB, you can launch the Shiny app directly from the command line:

``` bash
# Activate conda environment
conda activate rxnDB

# Launch app
rxndb
```

For more advanced usage, you can use the following options:

``` bash
# Activate conda environment
conda activate rxnDB

# rxndb --host 0.0.0.0   (Make accessible from other machines)
# rxndb --port 8080      (Run on a specific port)
# rxndb --launch-browser (Open browser automatically)
# rxndb --reload         (Auto-reload when files change)

# Default command
rxndb --host 127.0.0.1 --port 8000 --launch-browser --reload
```

## Coauthors

 - [Simon Hunt](https://research.manchester.ac.uk/en/persons/simon.hunt) (University of Manchester)
 - [John Wheeler](https://scholar.google.co.uk/citations?user=jsfp2-8AAAAJ&hl=en) (University of Liverpool)

## Acknowledgement

This work was funded by the UKRI NERC Large Grant no. NE/V018477/1 awarded to John Wheeler at the University of Liverpool.

