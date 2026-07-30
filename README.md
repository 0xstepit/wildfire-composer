# Wildfire Composer

A simple and minimalistic command-line (CLI) utility to generate wildfire
images.

## Usage

The usage instructions assumes you are an
[uv](https://docs.astral.sh/uv/concepts/tools/) user, if not, please adapt them
accordingly.

The project includes a `Makefile` that exposes command for the usage of the
project.

### Install

```sh
make install
```

### Notebooks

The `notebooks/` folder contains a simple notebook showcasing the usage of the
functions distributed with the project library. To run the notebook, please
first create a project-specific kernel:

```sh
make kernel
make start-jupyter
```

All notebooks are associated with a `.py` file to better format the code and
markdown content.

## References

1. [CEMS Mapping Data Docs](https://mapping.emergency.copernicus.eu/about/how-to-harvest-cems-mapping-data/)
