# donnees-synth-geo

## Get started on SSPCloud
- [Using VSCode and Python](https://datalab.sspcloud.fr/launcher/ide/vscode-python?name=vscode-python&version=2.2.4&s3=region-ec97c721&init.personalInit=«https%3A%2F%2Fraw.githubusercontent.com%2FInseeFrLab%2Fdata-reconstructio-from-tiles%2Frefs%2Fheads%2Fmain%2Finit-scripts%2Fvscode-python.sh»)

## Install the project
```sh
pip install -e .
```

## To load the input data

### Using bash
```sh
python scripts/download_FILO.py
python scripts/download_BAN.py
```

### Using Python
```python
from popdbgen import load_FILO, load_BAN
filo_974 = load_FILO("974")
ban_974 = load_BAN("974")
```


## To generate the household and population databases

### Using bash

```sh
python scripts/generate_database.py --territory 974
python scripts/generate_database.py --territory france --batchsize 100_000
```
See `python scripts/generate_database.py --help` for more options.

### Using Python
```python
from popdbgen import get_households_population_gdf
households, population = get_households_population_gdf(filo_df=filo, ban_df=ban)
```

## Tiling

The generated households database can be converted to a tiled format for data exploration.

`geopackage` files can be processed into the `mbtiles` tiled format using [`tippecanoe`](https://github.com/mapbox/tippecanoe):
<details>
  <summary> France </summary>

```sh
ogr2ogr -f GeoJSONSeq /vsistdout/ households_france.gpkg | tippecanoe -z15 --drop-densest-as-needed -P -o households_france.mbtiles -l households
ogr2ogr -f GeoJSONSeq /vsistdout/ carreaux_200m_met.gpkg | tippecanoe -z15 --drop-densest-as-needed -P -o carreaux_200m_met.mbtiles -l filo
```
</details>

<details>
  <summary> La Réunion </summary>

```sh
ogr2ogr -f GeoJSONSeq /vsistdout/ households_974.gpkg | tippecanoe -z15 --drop-densest-as-needed -P -o households_974.mbtiles -l households
ogr2ogr -f GeoJSONSeq /vsistdout/ carreaux_200m_reun.gpkg | tippecanoe -z15 --drop-densest-as-needed -P -o carreaux_200m_reun.mbtiles -l filo
```
</details>

Several `mbtiles` files can be joined in a single file in which datasets are represented as "layers":
```sh
tile-join -pk -o filo_households_france.mbtiles carreaux_200m_met.mbtiles households_france.mbtiles
tile-join -pk -o filo_households_974.mbtiles carreaux_200m_reun.mbtiles households_974.mbtiles
```
NOTE: While packing layers together is convenient for visualisation, it may not be the best option, for instance to embed the tiled data in a website.

The generated `mbtiles` can then be converted to the `pmtiles` format (`tippecanoe` tends to generate broken `pmtiles` files):
<details>
  <summary> France </summary>

```sh
pmtiles convert households_france.mbtiles households_france.pmtiles
pmtiles convert carreaux_200m_met.mbtiles carreaux_200m_met.pmtiles
pmtiles convert filo_households_france.mbtiles filo_households_france.pmtiles
```
</details>

<details>
  <summary> La Réunion </summary>

```sh
pmtiles convert households_974.mbtiles households_974.pmtiles
pmtiles convert carreaux_200m_reun.mbtiles carreaux_200m_reun.pmtiles
pmtiles convert filo_households_974.mbtiles filo_households_974.pmtiles
```
</details>

### `pmtiles` installation

```sh
wget https://github.com/protomaps/go-pmtiles/releases/download/v1.26.1/go-pmtiles_1.26.1_Linux_x86_64.tar.gz
tar -zxvf go-pmtiles_1.26.1_Linux_x86_64.tar.gz
```

### An online PMTiles viewer

[https://pmtiles.io/](https://pmtiles.io/)
