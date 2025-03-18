# Logging
LOGFILE := log/log-$(shell date +"%d-%m-%Y")
LOG := 2>&1 | tee -a $(LOGFILE)

# Conda config
CONDA_ENV_NAME := rxnDB
CONDA_SPECS_FILE := environment.yml
CONDA_PYTHON = $$(conda run -n $(CONDA_ENV_NAME) which python)

# Version
VERSION ?= $(shell git describe --tags --abbrev=0 2>/dev/null || echo "0.1.0")

# Cleanup directory
DATAPURGE := logs/ tmp/
DATACLEAN := __pycache__ *.pyc .pytest_cache build dist *.egg-info

all: create_conda_env

create_conda_env: $(CONDA_SPECS_FILE)
	@if conda env list | grep -q "$(CONDA_ENV_NAME)$$"; then \
		echo "  Conda environment '$(CONDA_ENV_NAME)' found!"; \
	else \
		echo "  Creating conda environment $(CONDA_ENV_NAME) ..."; \
		conda env create --file $(CONDA_SPECS_FILE); \
		echo "  Conda environment $(CONDA_ENV_NAME) created!"; \
	fi

update_version:
	@if uname | grep -q "Darwin"; then \
		sed -i '' 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml; \
	else \
		sed -i 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml; \
	fi
	@echo "Updated pyproject.toml to version $(VERSION)."

upload: build
	@twine upload dist/*
	@echo "Uploaded to PyPI."

build:
	@rm -rf build dist *.egg-info
	@python -m build
	@echo "Package built successfully."

purge:
	@rm -rf $(DATAPURGE)

clean: purge
	@rm -rf $(DATACLEAN)

.PHONY: clean purge build upload update_version create_conda_env all
