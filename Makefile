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
APP_DIR := rxnDB
APP_CLI := $(APP_DIR)/cli.py
APP_TESTS := tests/test_app.py
VERSION ?= $(shell git describe --tags --abbrev=0 2>/dev/null || echo "0.1.0")

# Datasets
DATA_DIR := $(APP_DIR)/data/
YML_DIRS := $(DATA_DIR)/sets/preprocessed/*

# Cleanup directory
DATAPURGE := logs/ tmp/
DATACLEAN := **/**/__pycache__ **/**/*.pyc .pytest_cache build dist *.egg-info $(YML_DIRS)

all: create_conda_env test_app run_app

run_app: $(APP_CLI)
	@$(CONDA_PYTHON) $(APP_CLI) --host 127.0.0.1 --port 8000 --launch-browser --reload

docs:
	@conda run -n $(CONDA_ENV_NAME) make -C docs html

docs_clean:
	@make -C docs clean

test_app: $()
	@$(CONDA_PYTHON) -m pytest $(APP_TESTS) -v

create_conda_env: $(CONDA_SPECS_FILE)
	@if conda env list | grep -q "$(CONDA_ENV_NAME)$$"; then \
		echo "  Conda environment '$(CONDA_ENV_NAME)' found!"; \
	else \
		echo "  Creating conda environment $(CONDA_ENV_NAME) ..."; \
		conda env create --file $(CONDA_SPECS_FILE); \
		echo "  Conda environment $(CONDA_ENV_NAME) created!"; \
	fi

$(LOGFILE):
	@mkdir -p log; [ -e "$(LOGFILE)" ] || touch $(LOGFILE)

purge:
	@rm -rf $(DATAPURGE)

clean: purge docs_clean
	@rm -rf $(DATACLEAN)

.PHONY: clean purge create_conda_env test_app docs_clean docs run_app all
