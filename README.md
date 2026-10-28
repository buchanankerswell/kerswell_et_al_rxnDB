# rxnDB: a mineral reaction database

📚 See the [documentation](https://kerswell-et-al-rxndb.readthedocs.io/en/latest/) for details.

## Prerequisite software

This project is written in [python](https://www.python.org). For most users, I recommend installing the [miniforge](https://github.com/conda-forge/miniforge) python distribution. This distributions includes a minimal installation of python and the package manager [conda](https://docs.conda.io/en/latest/), which is required to build the necessary python environment for this software.

For macOS users, miniforge can be installed with [homebrew](https://brew.sh):

```bash
brew install miniforge
```

For Window's users, miniforge can be installed from a binary .exe. Follow the instructions for miniconda, anaconda, or miniforge (recommended) [here](https://docs.conda.io/projects/conda/en/stable/user-guide/install/windows.html).

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
git clone https://github.com/buchanankerswell/rxndb.git
cd rxndb

# Checkout develop branch
git checkout develop

# Create conda environment and install rxnDB locally in editable mode
# including optional development and documentation dependencies
make environment
```

## Usage Guide

After installing rxnDB using either method above, launch the server from the command line:

``` bash
# Activate conda environment
conda activate rxnDB

# Launch server (UI at http://127.0.0.1:8000/)
rxndb
```

The same JSON serves browsers and agents:

``` bash
curl 'http://127.0.0.1:8000/reactions?mineral_symbol=Qz' | head -c 300
```

## Coauthors

 - [Simon Hunt](https://research.manchester.ac.uk/en/persons/simon.hunt) (University of Manchester)
 - [John Wheeler](https://scholar.google.co.uk/citations?user=jsfp2-8AAAAJ&hl=en) (University of Liverpool)

## Acknowledgement

The UKRI NERC Large Grant no. NE/V018477/1 awarded to John Wheeler at the University of Liverpool funded this work.

