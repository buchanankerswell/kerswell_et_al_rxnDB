# Logging
LOGFILE := log/log-$(shell date +"%d-%m-%Y")
LOG := 2>&1 | tee -a $(LOGFILE)

# Conda config
CONDA_ENV_NAME := rxnDB
CONDA_SPECS_FILE := environment.yml
CONDA_PYTHON = $$(conda run -n $(CONDA_ENV_NAME) which python)

# Cleanup directory
DATAPURGE :=
DATACLEAN :=
FIGSPURGE :=
FIGSCLEAN :=

all: create_conda_env

create_conda_env: $(CONDA_SPECS_FILE)
	@if conda env list | grep -q "$(CONDA_ENV_NAME)$$"; then \
		echo "  Conda environment '$(CONDA_ENV_NAME)' found!"; \
	else \
		echo "  Creating conda environment $(CONDA_ENV_NAME) ..."; \
		conda env create --file $(CONDA_SPECS_FILE); \
		echo "  Conda environment $(CONDA_ENV_NAME) created!"; \
	fi

purge:
	@rm -rf $(DATAPURGE) $(FIGSPURGE)

clean: purge
	@rm -rf $(DATACLEAN) $(FIGSCLEAN)

.PHONY: clean purge create_conda_env all
