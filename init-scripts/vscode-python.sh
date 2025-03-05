#!/bin/sh

# You may use this initialization script to easily setup an Onyxia "vscode-python" service
# https://datalab.sspcloud.fr/launcher/ide/vscode-python?name=vscode-python&init.personalInit=%C2%ABhttps%3A%2F%2Fraw.githubusercontent.com%2FJulienJamme%2Fdonnees-synth-geo%2Frefs%2Fheads%2Fmain%2Finit-scripts%2Fvscode-python.sh%C2%BB

sudo apt update -y
sudo apt install tree -y

# Clone project
cd ~/work/
git clone https://github.com/JulienJamme/donnees-synth-geo.git
cd donnees-synth-geo

# Install project (requirements and main package)
pip install -e .

# Replace default flake8 linter with project-preconfigured ruff
code-server --uninstall-extension ms-python.flake8
code-server --install-extension charliermarsh.ruff

# Install the mypy type checking extension and run type checking
pip install mypy
yes | mypy --install-types .
code-server --install-extension ms-python.mypy-type-checker

# Install and setup pre-commit
pip install pre-commit
pre-commit install
pre-commit run --all-files

# Download data
python scripts/download_FILO.py
python scripts/download_BAN.py
