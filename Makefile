.PHONY: help install kernel start-jupyter unit-tests

VENV = $(CURDIR)/.venv
KERNEL_NAME = wildfire-composer

help: ## Show available targets.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with uv.
	@uv sync

kernel: ## Create an IPython kernel for the project.
	@uv run ipython kernel install --user --env VIRTUAL_ENV $(VENV) --name=$(KERNEL_NAME)

start-jupyter: ## Start the Jupter Notebook server.
	@uv run jupyter-lab

unit-tests:
	@uv run pytest ./tests/ -v
