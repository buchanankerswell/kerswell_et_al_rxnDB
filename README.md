# rxnDB: a mineral reaction database

[![PyPI](https://img.shields.io/pypi/v/rxnDB)](https://pypi.org/project/rxnDB/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23736048.svg)](https://doi.org/10.5281/zenodo.23736048)

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

## Usage Guide

After installing rxnDB, launch the server from the command line:

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

## Citation

```bibtex
@software{rxndb,
  author       = {Kerswell, Buchanan},
  title        = {rxnDB: a mineral reaction database},
  month        = oct,
  year         = 2026,
  publisher    = {Zenodo},
  version      = {latest},
  doi          = {10.5281/zenodo.23736048},
  url          = {https://doi.org/10.5281/zenodo.23736048},
}
```

## Coauthors

 - [Simon Hunt](https://research.manchester.ac.uk/en/persons/simon.hunt) (University of Manchester)
 - [John Wheeler](https://scholar.google.co.uk/citations?user=jsfp2-8AAAAJ&hl=en) (University of Liverpool)

## Acknowledgement

The UKRI NERC Large Grant no. NE/V018477/1 awarded to John Wheeler at the University of Liverpool funded this work.

