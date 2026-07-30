.PHONY: install kernel start-jupyter

venv = $(CURDIR)/.venv
kernel_name = geosptial-misc

install:
	@uv sync

kernel:
	@uv run ipython kernel install --user --env VIRTUAL_ENV $(venv) --name=$(kernel_name)

start-jupyter:
	@uv run jupyter-lab
