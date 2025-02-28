#!/bin/sh

# You may use this initialization script to easily setup an Onyxia "vscode-python" service
# https://datalab.sspcloud.fr/launcher/ide/vscode-python?name=vscode-python&init.personalInit=%C2%ABhttps%3A%2F%2Fraw.githubusercontent.com%2FGaspi%2Fdonnees-synth-geo%2Frefs%2Fheads%2Fmain%2Finit-scripts%2Fvscode-python.sh%C2%BB

sudo apt update -y
sudo apt install tree -y

# Clone project
cd ~/work/
git clone https://github.com/Gaspi/donnees-synth-geo.git
cd donnees-synth-geo

# Install requirements and run linting on project
pip install -r requirements.txt

# Replace default flake8 linter with project-preconfigured ruff
code-server --uninstall-extension ms-python.flake8
code-server --install-extension charliermarsh.ruff

# Install type checking extension
code-server --install-extension ms-python.mypy-type-checker

yes | mypy --install-types

pip install pre-commit
pre-commit install
pre-commit run --all-files
