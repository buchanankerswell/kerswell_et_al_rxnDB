# Logging
LOGFILE := log/log-$(shell date +"%d-%m-%Y")
LOG := 2>&1 | tee -a $(LOGFILE)

# Conda config
CONDA_ENV_NAME := rxnDB
CONDA_SPECS_FILE := environment.yml
CONDA_PYTHON = $$(conda run -n $(CONDA_ENV_NAME) which python)
CONDA_SHINY = $$(conda run -n $(CONDA_ENV_NAME) which shiny)
DOC_DEPS = docs/requirements.txt

# Shiny app
APP := rxnDB/app.py
VERSION ?= $(shell git describe --tags --abbrev=0 2>/dev/null || echo "0.1.0")

# Cleanup directory
DATAPURGE := logs/ tmp/
DATACLEAN := **/**/__pycache__ **/**/*.pyc .pytest_cache build dist *.egg-info

all: create_conda_env run_app

run_app: $(APP)
	@$(CONDA_SHINY) run --reload --launch-browser $(APP)

create_conda_env: $(CONDA_SPECS_FILE)
	@if conda env list | grep -q "$(CONDA_ENV_NAME)$$"; then \
		echo "  Conda environment '$(CONDA_ENV_NAME)' found!"; \
	else \
		echo "  Creating conda environment $(CONDA_ENV_NAME) ..."; \
		conda env create --file $(CONDA_SPECS_FILE); \
		echo "  Conda environment $(CONDA_ENV_NAME) created!"; \
	fi
	@echo "  Installing rxnDB in editable mode ..."
	@conda run -n $(CONDA_ENV_NAME) pip install -e ".[dev,docs]"
	@echo "  Installing documentation dependencies ..."
	@conda run -n $(CONDA_ENV_NAME) pip install -r $(DOC_DEPS)

purge:
	@rm -rf $(DATAPURGE)

clean: purge
	@rm -rf $(DATACLEAN)

.PHONY: clean purge create_conda_env all
