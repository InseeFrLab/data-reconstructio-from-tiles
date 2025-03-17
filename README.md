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
python scripts/main.py -t 974
```

### Using Python
```python
from popdbgen import get_households_population_gdf
households, population = get_households_population_gdf(filo_df=filo, ban_df=ban)
```
