#!/bin/bash
# screen
# ./init-scripts/full-generation.sh > logs.txt 2>&1
# Ctrl-A D
# tail logs.txt -f
# Ctrl-C

set -o xtrace

PROJECT_DIR=/home/onyxia/work/data-reconstructio-from-tiles
DATA_DIR=$PROJECT_DIR/data
S3_PATH=s3/mybucket/diffusion/synth-filo

# Generate household and population databases
cd $PROJECT_DIR
pip install -e .
python scripts/download_FILO.py
python scripts/download_BAN.py

# Install Tippecanoe
mkdir -p $DATA_DIR
cd $DATA_DIR
git clone https://github.com/felt/tippecanoe.git
cd tippecanoe
make -j
sudo make install



# 972

## Generation: gpkg
cd $PROJECT_DIR
# python scripts/generate_database.py --datadir $DATA_DIR --geopackage --geoparquet -v --territory 972
cd $DATA_DIR

## FILO: gpkg upload
mc cp $DATA_DIR/carreaux_200m_mart.gpkg $S3_PATH/972/filo_200m/filo_200m_972.gpkg

## FILO: gpkg -> mbtiles
ogr2ogr -f GeoJSONSeq /vsistdout/ carreaux_200m_mart.gpkg | tippecanoe -z15 --coalesce-densest-as-needed -ab -P -o filo_200m_972.mbtiles -l filo
mc cp filo_200m_972.mbtiles $S3_PATH/972/filo_200m/filo_200m_972.mbtiles
rm carreaux_200m_mart.gpkg

## FILO: mbtiles -> pmtiles
pmtiles convert filo_200m_972.mbtiles filo_200m_972.pmtiles
mc cp filo_200m_972.pmtiles $S3_PATH/972/filo_200m/filo_200m_972.pmtiles
rm filo_200m_972.pmtiles



# 974

## Generation: gpkg
cd $PROJECT_DIR
python scripts/generate_database.py --datadir $DATA_DIR --geopackage --geoparquet -v --territory 974
cd $DATA_DIR

## FILO: gpkg upload
mc cp $DATA_DIR/carreaux_200m_reun.gpkg $S3_PATH/974/filo_200m/filo_200m_974.gpkg

## FILO: gpkg -> mbtiles
ogr2ogr -f GeoJSONSeq /vsistdout/ carreaux_200m_reun.gpkg | tippecanoe -l filo -z15 --coalesce-densest-as-needed -ab -P -o filo_200m_974.mbtiles
mc cp filo_200m_974.mbtiles $S3_PATH/974/filo_200m/filo_200m_974.mbtiles
rm carreaux_200m_reun.gpkg

## FILO: mbtiles -> pmtiles
pmtiles convert filo_200m_974.mbtiles filo_200m_974.pmtiles
mc cp filo_200m_974.pmtiles $S3_PATH/974/filo_200m/filo_200m_974.pmtiles
rm filo_200m_974.pmtiles

## Upload: gpkg, parquet, yaml
mc cp households_974.gpkg    $S3_PATH/974/households/households_974.gpkg
mc cp population_974.gpkg    $S3_PATH/974/population/population_974.gpkg
mc cp households_974.parquet $S3_PATH/974/households/households_974.parquet
mc cp population_974.parquet $S3_PATH/974/population/population_974.parquet
mc cp households_974.yaml    $S3_PATH/974/households/households_974.yaml
mc cp population_974.yaml    $S3_PATH/974/population/population_974.yaml
rm households_974.parquet
rm population_974.parquet
rm households_974.yaml
rm population_974.yaml

## Households: gpkg -> mbtiles
ogr2ogr -f GeoJSONSeq /vsistdout/ households_974.gpkg | tippecanoe -l households -z15 --drop-densest-as-needed -P -o households_974.mbtiles
mc cp households_974.mbtiles $S3_PATH/974/households/households_974.mbtiles
rm households_974.gpkg

## Households: mbtiles -> pmtiles
pmtiles convert households_974.mbtiles households_974.pmtiles
mc cp households_974.pmtiles $S3_PATH/974/households/households_974.pmtiles
rm households_974.pmtiles

## Households + FILO -> mbtiles
tile-join -pk -o filo_households_974.mbtiles filo_200m_974.mbtiles households_974.mbtiles
mc cp filo_households_974.mbtiles $S3_PATH/974/households/filo_households_974.mbtiles
rm households_974.mbtiles

## Households + FILO: mbtiles -> pmtiles
pmtiles convert filo_households_974.mbtiles filo_households_974.pmtiles
mc cp filo_households_974.pmtiles $S3_PATH/974/households/filo_households_974.pmtiles
rm filo_households_974.pmtiles
rm filo_households_974.mbtiles

## Population: gpkg -> mbtiles
ogr2ogr -f GeoJSONSeq /vsistdout/ population_974.gpkg | tippecanoe -l population -z15 --drop-densest-as-needed -P -o population_974.mbtiles
mc cp population_974.mbtiles $S3_PATH/974/population/population_974.mbtiles
rm population_974.gpkg

## Population: mbtiles -> pmtiles
pmtiles convert population_974.mbtiles population_974.pmtiles
mc cp population_974.pmtiles $S3_PATH/974/population/population_974.pmtiles
rm population_974.pmtiles


## Population + FILO -> mbtiles
tile-join -pk -o filo_population_974.mbtiles filo_200m_974.mbtiles population_974.mbtiles
mc cp filo_population_974.mbtiles $S3_PATH/974/population/filo_population_974.mbtiles
rm population_974.mbtiles

rm filo_200m_974.mbtiles

## Population + FILO: mbtiles -> pmtiles
pmtiles convert filo_population_974.mbtiles filo_population_974.pmtiles
mc cp filo_population_974.pmtiles $S3_PATH/974/population/filo_population_974.pmtiles
rm filo_population_974.pmtiles
rm filo_population_974.mbtiles



# METRO

## Generation: gpkg
cd $PROJECT_DIR
python $PROJECT_DIR/scripts/generate_database.py --datadir $DATA_DIR --geopackage --geoparquet -v --territory METRO --batchsize 100_000
cd $DATA_DIR

## FILO: gpkg upload
mc cp $DATA_DIR/carreaux_200m_met.gpkg $S3_PATH/METRO/filo_200m/filo_200m_METRO.gpkg

## FILO: gpkg -> mbtiles
ogr2ogr -f GeoJSONSeq /vsistdout/ carreaux_200m_met.gpkg | tippecanoe -l filo -Z11 -z16               -P -o filo_200m_METRO_z11-16.mbtiles
ogr2ogr -f GeoJSONSeq /vsistdout/ carreaux_200m_met.gpkg | tippecanoe -l filo -Z8  -z10 -X --coalesce -P -o filo_200m_METRO_z8-10.mbtiles
tile-join -o filo_200m_METRO.mbtiles filo_200m_METRO_z11-16.mbtiles filo_200m_METRO_z8-10.mbtiles
rm filo_200m_METRO_z11-16.mbtiles
rm filo_200m_METRO_z8-10.mbtiles
mc cp filo_200m_METRO.mbtiles $S3_PATH/METRO/filo_200m/filo_200m_METRO.mbtiles
rm carreaux_200m_met.gpkg

## FILO: mbtiles -> pmtiles
pmtiles convert filo_200m_METRO.mbtiles filo_200m_METRO.pmtiles
mc cp filo_200m_METRO.pmtiles $S3_PATH/METRO/filo_200m/filo_200m_METRO.pmtiles
rm filo_200m_METRO.pmtiles

## Upload: gpkg, parquet, yaml
mc cp households_METRO.gpkg    $S3_PATH/METRO/households/households_METRO.gpkg
mc cp population_METRO.gpkg    $S3_PATH/METRO/population/population_METRO.gpkg
mc cp households_METRO.parquet $S3_PATH/METRO/households/households_METRO.parquet
mc cp population_METRO.parquet $S3_PATH/METRO/population/population_METRO.parquet
mc cp households_METRO.yaml    $S3_PATH/METRO/households/households_METRO.yaml
mc cp population_METRO.yaml    $S3_PATH/METRO/population/population_METRO.yaml
rm households_METRO.parquet
rm population_METRO.parquet
rm households_METRO.yaml
rm population_METRO.yaml




## Households: gpkg -> mbtiles
ogr2ogr -f GeoJSONSeq /vsistdout/ households_METRO.gpkg | tippecanoe -l households -z14 --drop-densest-as-needed -P -o households_METRO_14.mbtiles
ogr2ogr -f GeoJSONSeq /vsistdout/ households_METRO.gpkg | tippecanoe -l households -Z15 -z15                     -P -o households_METRO_15.mbtiles
rm households_METRO.gpkg
tile-join -o households_METRO.mbtiles households_METRO_14.mbtiles households_METRO_15.mbtiles
mc cp households_METRO.mbtiles $S3_PATH/METRO/households/households_METRO.mbtiles
rm households_METRO_14.mbtiles
rm households_METRO_15.mbtiles

## Households: mbtiles -> pmtiles
pmtiles convert households_METRO.mbtiles households_METRO.pmtiles
mc cp households_METRO.pmtiles $S3_PATH/METRO/households/households_METRO.pmtiles
rm households_METRO.pmtiles

## Households + FILO -> mbtiles
tile-join -pk -o filo_households_METRO.mbtiles filo_200m_METRO.mbtiles households_METRO.mbtiles
mc cp filo_households_METRO.mbtiles $S3_PATH/METRO/households/filo_households_METRO.mbtiles
rm households_METRO.mbtiles

## Households + FILO: mbtiles -> pmtiles
pmtiles convert filo_households_METRO.mbtiles filo_households_METRO.pmtiles
mc cp filo_households_METRO.pmtiles $S3_PATH/METRO/households/filo_households_METRO.pmtiles
rm filo_households_METRO.pmtiles
rm filo_households_METRO.mbtiles

## Population: gpkg -> mbtiles
ogr2ogr -f GeoJSONSeq /vsistdout/ population_METRO.gpkg | tippecanoe -l population -z15 --drop-densest-as-needed -P -o population_METRO_15.mbtiles
ogr2ogr -f GeoJSONSeq /vsistdout/ population_METRO.gpkg | tippecanoe -l population -Z16 -z16                     -P -o population_METRO_16.mbtiles
rm population_METRO.gpkg
tile-join -o population_METRO.mbtiles population_METRO_15.mbtiles population_METRO_16.mbtiles
mc cp population_METRO.mbtiles $S3_PATH/METRO/population/population_METRO.mbtiles
rm population_METRO_15.mbtiles
rm population_METRO_16.mbtiles

## Population: mbtiles -> pmtiles
pmtiles convert population_METRO.mbtiles population_METRO.pmtiles
mc cp population_METRO.pmtiles $S3_PATH/METRO/population/population_METRO.pmtiles
rm population_METRO.pmtiles


## Population + FILO -> mbtiles
tile-join -pk -o filo_population_METRO.mbtiles filo_200m_METRO.mbtiles population_METRO.mbtiles
mc cp filo_population_METRO.mbtiles $S3_PATH/METRO/population/filo_population_METRO.mbtiles
rm population_METRO.mbtiles

rm filo_200m_METRO.mbtiles

## Population + FILO: mbtiles -> pmtiles
pmtiles convert filo_population_METRO.mbtiles filo_population_METRO.pmtiles
mc cp filo_population_METRO.pmtiles $S3_PATH/METRO/population/filo_population_METRO.pmtiles
rm filo_population_METRO.pmtiles
rm filo_population_METRO.mbtiles



# Done
echo "Done"
