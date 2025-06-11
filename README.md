# donnees-synth-geo

## Get started on SSPCloud
- [Using VSCode and Python](https://datalab.sspcloud.fr/launcher/ide/vscode-python?name=synth-data&init.personalInit=«https%3A%2F%2Fraw.githubusercontent.com%2FInseeFrLab%2Fdata-reconstructio-from-tiles%2Frefs%2Fheads%2Fmain%2Finit-scripts%2Fvscode-python.sh»)

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
python scripts/generate_database.py --territory METRO --batchsize 100_000
```
See `python scripts/generate_database.py --help` for more options.

### Using Python
```python
from popdbgen import get_households_population_gdf
households, population = get_households_population_gdf(filo_df=filo, ban_df=ban)
```

## Tiling

The generated households database can be converted to a tiled format for data exploration.

`geopackage` files can be processed into the `mbtiles` tiled format using [`tippecanoe`](https://github.com/felt/tippecanoe):
<details>
  <summary> Métropole </summary>

Generate tiles for households points
```sh
ogr2ogr -f GeoJSONSeq /vsistdout/ households_METRO.gpkg | tippecanoe -z14 --drop-densest-as-needed -P -o households_METRO_14.mbtiles -l households
ogr2ogr -f GeoJSONSeq /vsistdout/ households_METRO.gpkg | tippecanoe -Z15 -z15 -P -o households_METRO_15.mbtiles -l households
tile-join -o households_METRO.mbtiles households_METRO_14.mbtiles households_METRO_15.mbtiles
rm households_METRO_14.mbtiles households_METRO_15.mbtiles
```

Generate tiles for population points
```sh
ogr2ogr -f GeoJSONSeq /vsistdout/ population_METRO.gpkg | tippecanoe -z15 --drop-densest-as-needed -P -o population_METRO_15.mbtiles -l population
ogr2ogr -f GeoJSONSeq /vsistdout/ population_METRO.gpkg | tippecanoe -Z16 -z16 -P -o population_METRO_16.mbtiles -l population
tile-join -o population_METRO.mbtiles population_METRO_15.mbtiles population_METRO_16.mbtiles
rm population_METRO_15.mbtiles population_METRO_16.mbtiles
```

Generate FILO tiles
```sh
# The FILO tiles are too numerous to be represented at higher zoom levels for Metropolitan France
# Zoom levels 11-16: generate tiles without simplification
ogr2ogr -f GeoJSONSeq /vsistdout/ carreaux_200m_met.gpkg | tippecanoe -l filo -Z11 -z16 -P -o carreaux_200m_met_z11-16.mbtiles
# Zoom levels 8-10: drop attributes and coalesce geometries
ogr2ogr -f GeoJSONSeq /vsistdout/ carreaux_200m_met.gpkg | tippecanoe -l filo -Z8  -z10 -P -X --coalesce -o carreaux_200m_met_z8-10.mbtiles
# Zoom levels 0-7: no tile generated
tile-join -o carreaux_200m_met.mbtiles carreaux_200m_met_z11-16.mbtiles carreaux_200m_met_z8-10.mbtiles
rm carreaux_200m_met_z11-16.mbtiles carreaux_200m_met_z8-10.mbtiles
```
</details>

<details>
  <summary> La Réunion </summary>

```sh
ogr2ogr -f GeoJSONSeq /vsistdout/ households_974.gpkg | tippecanoe -z15 --drop-densest-as-needed -P -o households_974.mbtiles -l households
ogr2ogr -f GeoJSONSeq /vsistdout/ population_974.gpkg | tippecanoe -z15 --drop-densest-as-needed -P -o population_974.mbtiles -l population
ogr2ogr -f GeoJSONSeq /vsistdout/ carreaux_200m_reun.gpkg | tippecanoe -z15 --coalesce-densest-as-needed -ab -P -o carreaux_200m_reun.mbtiles -l filo
```
</details>

Several `mbtiles` files can be joined in a single file in which datasets are represented as "layers":
```sh
tile-join -pk -o filo_households_METRO.mbtiles carreaux_200m_met.mbtiles households_METRO.mbtiles
tile-join -pk -o filo_population_METRO.mbtiles carreaux_200m_met.mbtiles population_METRO.mbtiles

tile-join -pk -o filo_households_974.mbtiles carreaux_200m_reun.mbtiles households_974.mbtiles
tile-join -pk -o filo_population_974.mbtiles carreaux_200m_reun.mbtiles population_974.mbtiles
```
NOTE: While packing layers together is convenient for visualisation, it may not be the best option, for instance to embed the tiled data in a website.

The generated `mbtiles` can then be converted to the `pmtiles` format (`tippecanoe` tends to generate broken `pmtiles` files):
<details>
  <summary> Métropole </summary>

```sh
pmtiles convert carreaux_200m_met.mbtiles carreaux_200m_met.pmtiles
pmtiles convert households_METRO.mbtiles households_METRO.pmtiles
pmtiles convert filo_households_METRO.mbtiles filo_households_METRO.pmtiles
pmtiles convert population_METRO.mbtiles population_METRO.pmtiles
pmtiles convert filo_population_METRO.mbtiles filo_population_METRO.pmtiles
```
</details>

<details>
  <summary> La Réunion </summary>

```sh
pmtiles convert carreaux_200m_reun.mbtiles carreaux_200m_reun.pmtiles
pmtiles convert households_974.mbtiles households_974.pmtiles
pmtiles convert filo_households_974.mbtiles filo_households_974.pmtiles
pmtiles convert population_974.mbtiles population_974.pmtiles
pmtiles convert filo_population_974.mbtiles filo_population_974.pmtiles
```
</details>

### `tippecanoe` installation

```sh
git clone https://github.com/felt/tippecanoe.git
cd tippecanoe
make -j
sudo make install
```

### `pmtiles` installation

```sh
wget https://github.com/protomaps/go-pmtiles/releases/download/v1.26.1/go-pmtiles_1.26.1_Linux_x86_64.tar.gz
tar -zxvf go-pmtiles_1.26.1_Linux_x86_64.tar.gz
sudo cp pmtiles /usr/local/bin/
```

### An online PMTiles viewer

[https://pmtiles.io/](https://pmtiles.io/)


## Push to S3

Set environment variables
```sh
DATA_DIR=/your/data/dir
S3_PATH=s3/bucket/path/to/dir
```

Upload all generated files to S3
<details>
  <summary> La Réunion </summary>

```sh
# 972
mc cp $DATA_DIR/carreaux_200m_mart.gpkg $S3_PATH/972/filo_200m/filo_200m_972.gpkg
```
</details>

<details>
  <summary> La Réunion </summary>

```sh
mc cp $DATA_DIR/carreaux_200m_reun.gpkg $S3_PATH/974/filo_200m/filo_200m_974.gpkg
mc cp $DATA_DIR/carreaux_200m_reun.mbtiles $S3_PATH/974/filo_200m/filo_200m_974.mbtiles
mc cp $DATA_DIR/carreaux_200m_reun.pmtiles $S3_PATH/974/filo_200m/filo_200m_974.pmtiles

mc cp $DATA_DIR/households_974.gpkg $S3_PATH/974/households/households_974.gpkg
mc cp $DATA_DIR/households_974.parquet $S3_PATH/974/households/households_974.parquet
mc cp $DATA_DIR/households_974.yaml $S3_PATH/974/households/households_974.yaml
mc cp $DATA_DIR/households_974.mbtiles $S3_PATH/974/households/households_974.mbtiles
mc cp $DATA_DIR/households_974.pmtiles $S3_PATH/974/households/households_974.pmtiles
mc cp $DATA_DIR/filo_households_974.mbtiles $S3_PATH/974/households/filo_households_974.mbtiles
mc cp $DATA_DIR/filo_households_974.pmtiles $S3_PATH/974/households/filo_households_974.pmtiles

mc cp $DATA_DIR/population_974.gpkg $S3_PATH/974/population/population_974.gpkg
mc cp $DATA_DIR/population_974.parquet $S3_PATH/974/population/population_974.parquet
mc cp $DATA_DIR/population_974.yaml $S3_PATH/974/population/population_974.yaml
mc cp $DATA_DIR/population_974.mbtiles $S3_PATH/974/population/population_974.mbtiles
mc cp $DATA_DIR/population_974.pmtiles $S3_PATH/974/population/population_974.pmtiles
mc cp $DATA_DIR/filo_population_974.mbtiles $S3_PATH/974/population/filo_population_974.mbtiles
mc cp $DATA_DIR/filo_population_974.pmtiles $S3_PATH/974/population/filo_population_974.pmtiles
```
</details>

<details>
  <summary> Métropole </summary>

```sh
mc cp $DATA_DIR/carreaux_200m_met.gpkg $S3_PATH/METRO/filo_200m/filo_200m_METRO.gpkg
mc cp $DATA_DIR/carreaux_200m_met.mbtiles $S3_PATH/METRO/filo_200m/filo_200m_METRO.mbtiles
mc cp $DATA_DIR/carreaux_200m_met.pmtiles $S3_PATH/METRO/filo_200m/filo_200m_METRO.pmtiles

mc cp $DATA_DIR/households_METRO.gpkg $S3_PATH/METRO/households/households_METRO.gpkg
mc cp $DATA_DIR/households_METRO.parquet $S3_PATH/METRO/households/households_METRO.parquet
mc cp $DATA_DIR/households_METRO.yaml $S3_PATH/METRO/households/households_METRO.yaml
mc cp $DATA_DIR/households_METRO.mbtiles $S3_PATH/METRO/households/households_METRO.mbtiles
mc cp $DATA_DIR/households_METRO.pmtiles $S3_PATH/METRO/households/households_METRO.pmtiles
mc cp $DATA_DIR/filo_households_METRO.mbtiles $S3_PATH/METRO/households/filo_households_METRO.mbtiles
mc cp $DATA_DIR/filo_households_METRO.pmtiles $S3_PATH/METRO/households/filo_households_METRO.pmtiles

mc cp $DATA_DIR/population_METRO.gpkg $S3_PATH/METRO/population/population_METRO.gpkg
mc cp $DATA_DIR/population_METRO.parquet $S3_PATH/METRO/population/population_METRO.parquet
mc cp $DATA_DIR/population_METRO.yaml $S3_PATH/METRO/population/population_METRO.yaml
mc cp $DATA_DIR/population_METRO.mbtiles $S3_PATH/METRO/population/population_METRO.mbtiles
mc cp $DATA_DIR/population_METRO.pmtiles $S3_PATH/METRO/population/population_METRO.pmtiles
mc cp $DATA_DIR/filo_population_METRO.mbtiles $S3_PATH/METRO/population/filo_population_METRO.mbtiles
mc cp $DATA_DIR/filo_population_METRO.pmtiles $S3_PATH/METRO/population/filo_population_METRO.pmtiles
```
</details>
