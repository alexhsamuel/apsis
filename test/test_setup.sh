#!/bin/bash

unset PYTHONPATH

set -e

conda create -n apsis-setup-test --yes python=3.6
source activate apsis-setup-test

pip install .

python -m apsis.service.main --help > /dev/null
apsis --help > /dev/null

source deactivate

conda env remove -n apsis-setup-test --yes

echo "success"

