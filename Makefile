# Top-level dirs
PROJECT_ROOT := $(CURDIR)
APP := $(PROJECT_ROOT)/rxnDB
TESTS := $(PROJECT_ROOT)/tests
DOCS := $(PROJECT_ROOT)/docs

# Conda config
CONDA_ENV_ID := rxnDB
CONDA_ENV_YML := environment.yml
CONDA_PYTHON = $$(conda run -n $(CONDA_ENV_ID) which python)

# Shiny app
APP_CLI := $(APP)/cli.py

# Cleanup directory
CLEAN := $(APP)/**/__pycache__ $(APP)/**/*.pyc $(TESTS)/**/__pycache__ $(CURDIR)/.pytest_cache $(CURDIR)/build $(CURDIR)/dist $(CURDIR)/*.egg-info $(CURDIR)/.coverage $(CURDIR)/coverage.xml
DEEP_CLEAN :=

# Targets
.PHONY: run docs test environment clean deep-clean

all: environment test run

run: $(APP_CLI)
	@$(CONDA_PYTHON) $(APP_CLI) --host 127.0.0.1 --port 8000 --launch-browser --reload

docs:
	@$(MAKE) -C docs html

test:
	@$(CONDA_PYTHON) -m pytest --cov=rxnDB --cov-branch --cov-report=xml

environment: $(CONDA_ENV_YML)
	@if conda info --envs | awk '{print $$1}' | grep -qx "$(CONDA_ENV_ID)"; then \
		echo "Environment '$$name' already exists. Skipping..."; \
	else \
		echo "Creating environment: $(CONDA_ENV_ID) from $(CONDA_ENV_YML)"; \
		conda env create -n "$(CONDA_ENV_ID)" -f "$(CONDA_ENV_YML)"; \
	fi

clean:
	@echo "==> Cleaning ..."
	@for item in $(CLEAN); do \
		safe_rm() { \
			if [ -e "$$1" ]; then \
				ABS_PATH=$$(realpath "$$1"); \
				case "$$ABS_PATH" in \
					$(PROJECT_ROOT)*) \
						echo "-> Safely removing\n   $$ABS_PATH"; \
						rm -rf "$$ABS_PATH";; \
					*) \
						echo "!! Skipping (outside project root)\n   $$ABS_PATH";; \
				esac; \
			else \
				echo "-- Skipping (not found)\n   $$1"; \
			fi; \
		}; \
		safe_rm "$$item"; \
	done
	@$(MAKE) -C docs clean || true
	@find . -name ".DS_Store" -type f -delete

deep-clean:
	@echo "==> Deep cleaning ..."
	@for item in $(DEEP_CLEAN); do \
		safe_rm() { \
			if [ -e "$$1" ]; then \
				ABS_PATH=$$(realpath "$$1"); \
				case "$$ABS_PATH" in \
					$(PROJECT_ROOT)*) \
						echo "-> Safely removing\n   $$ABS_PATH"; \
						rm -rf "$$ABS_PATH";; \
					*) \
						echo "!! Skipping (outside project root)\n   $$ABS_PATH";; \
				esac; \
			else \
				echo "-- Skipping (not found)\n   $$1"; \
			fi; \
		}; \
		safe_rm "$$item"; \
	done


help:
	@echo "Available targets:"
	@echo "  run          Run rxnDB app locally"
	@echo "  docs         Build documentation"
	@echo "  test         Run unit tests"
	@echo "  environment  Create Conda environment"
	@echo "  clean        Cleanup unnecessary files and directories (safe)"
	@echo "  deep-clean   Deep clean figures and results (use with caution!)"
	@echo "  help         Show this help message"
