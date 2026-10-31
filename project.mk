PROJECT_ROOT := $(realpath $(dir $(lastword $(MAKEFILE_LIST)))/.)

CONDA_ENV_ID := rxnDB
CONDA_ENV_YML := environment.yml
APP_MODULE := rxnDB.api:app
HOST := 127.0.0.1
SERVE_PORT := 8000
APP := $(PROJECT_ROOT)/rxnDB
TESTS := $(PROJECT_ROOT)/tests
DOCS := $(PROJECT_ROOT)/docs
CONDA_PYTHON = $$(conda run -n $(CONDA_ENV_ID) which python)
CLEAN := $(PROJECT_ROOT)/.pytest_cache \
         $(PROJECT_ROOT)/build \
         $(PROJECT_ROOT)/dist \
         $(PROJECT_ROOT)/*.egg-info \
         $(PROJECT_ROOT)/.coverage \
         $(PROJECT_ROOT)/coverage.xml
DEEP_CLEAN := $(PROJECT_ROOT)/.log $(DOCS)/_build

DATE := $(shell date +"%d-%m-%Y")
LOG_FILE := $(PROJECT_ROOT)/.log/log-$(DATE).log
LOGGER := 2>&1 | tee -a $(LOG_FILE)

define SAFE_RM
	if [ -e "$(1)" ]; then \
	  ABS_PATH=$$(realpath "$(1)"); \
	  case "$$ABS_PATH" in \
	    $(PROJECT_ROOT)*) \
	      echo " xx $$ABS_PATH"; \
	      rm -rf "$$ABS_PATH";; \
	  esac; \
	fi
endef

define SAFE_RM_LIST
	for item in $(1); do $(call SAFE_RM,$$item); done
endef
