#!/bin/sh

# You may use this init script to setup an Onyxia service
# https://datalab.sspcloud.fr/launcher/ide/vscode-python?resources.requests.cpu=%C2%AB1000m%C2%BB&resources.requests.memory=%C2%AB32Gi%C2%BB&resources.limits.memory=%C2%AB100Gi%C2%BB&persistence.size=%C2%AB50Gi%C2%BB&git.repository=%C2%ABhttps%3A%2F%2Fgithub.com%2Fjulienjamme%2Fdonnees-synth-geo.git%C2%BB

sudo apt update -y
sudo apt install tree -y

# Clone project
cd ~/work/
git clone https://github.com/julienjamme/donnees-synth-geo.git
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
