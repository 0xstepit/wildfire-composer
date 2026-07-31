[![CC BY 4.0][cc-by-shield]][cc-by]

# Wildfire Composer

A simple and minimalistic command-line (CLI) utility to generate wildfire
composite rasters and images from Rapid Mapping CEMS activations and the
Sentinel-2 data.

![Wildfire Composite](./data/images/wildfire_mosaic.png)

## Usage

The usage instructions assume you are a
[uv](https://docs.astral.sh/uv/concepts/tools/) user; if not, please adapt them
accordingly.

The project includes a `Makefile` to simplify common commands.

### Install

```sh
make install
```

The project is installed as an editable package. Now, you can run the CLI:

```sh
uv run wildfire-composer
```

The CLI exposes three commands:

- `refresh`: populate a DuckDB database containing all the Rapid Mapping
  activations.
- `list`: display a table containing available activations.
- `render`: create a composite raster using the report bounding box, store the
  pre- and post-fire scenes as a `.zarr` file, and generate an image
  representing the wildfire.

CLI parameters can be configured either via environment variables or by updating
the associated configuration file in `config/config.toml`. If you opt for the
first option, please:

```sh
cp .env.example .env
```

And populate the variables you want to customize.

### Notebooks

The `notebooks/` folder contains a simple notebook showcasing how to use the
`mosaic()` function to generate the cover image from the raster composites. To
run the notebook, please first create a project-specific kernel:

```sh
make kernel
make start-jupyter
```

## Disclaimer

The project is a work in progress and has been developed mainly to quickly
visualize CEMS reports in a nice way such that composite mosaics can be shared.
For this reason, expect bugs, no tests, and possible failures during the
generation of the composites.

For the moment, the code supports only CEMS reports with a completed grading
product attached. That said, the project can easily be extended to:

- Automatically draw a bounding box around the center, without using the one
  provided in the report.
- Use the complete CEMS activations list, not only the Rapid Mapping subset, to
  have access to more wildfire points.
- Improve the CLI to accept more customization from the user for raster
  composition, image generation, and data search.
- Generate a ready-to-go dataset of all the CEMS wildfires to facilitate
  data-driven analysis.
- Use the Harmonized Landsat Sentinel-2 dataset to have a better temporal
  resolution of the analyzed areas.

## Contributing

Pull requests, bug reports, and all other forms of contribution are welcome and
highly encouraged!

## License

This work is licensed under a
[Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).

## References

1. [CEMS Mapping Data Docs](https://mapping.emergency.copernicus.eu/about/how-to-harvest-cems-mapping-data/)
1. [Emergency Response Data](https://mapping.emergency.copernicus.eu/about/how-to-harvest-cems-mapping-data/emergency-response-data/)

[cc-by]: http://creativecommons.org/licenses/by/4.0/
[cc-by-shield]: https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg
