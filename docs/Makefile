include ../project.mk

SPHINX_BUILD := sphinx-build
SPHINX_OPTS ?=
SOURCE_DIR := $(DOCS)
BUILD_DIR := $(DOCS)/_build
CLEAN := $(BUILD_DIR)/*

.PHONY: help Makefile

help:
	@$(SPHINX_BUILD) -M help "$(SOURCE_DIR)" "$(BUILD_DIR)" $(SPHINX_OPTS) $(O)

%: Makefile
	@$(SPHINX_BUILD) -M $@ "$(SOURCE_DIR)" "$(BUILD_DIR)" $(SPHINX_OPTS) $(O)

# Guard: the '%: Makefile' catch-all must not rebuild project.mk.
../project.mk: ;

clean:
	@$(call SAFE_RM_LIST,$(CLEAN))
