#!/bin/sh

set -e

#PUPA_ENV=~/.virtualenvs/pupa
#BILLY_ENV=~/.virtualenvs/openstates

# copy use shift to get rid of first param, pass rest to pupa update
state=$1
shift

export PYTHONPATH=./scrapers
$PUPA_ENV/bin/pupa update $state --scrape "$@"
export PUPA_DATA_DIR='../openstates/_data'
export PYTHONPATH=./billy_metadata/
$BILLY_ENV/bin/python -m pupa2billy.run $state
$BILLY_ENV/bin/billy-update $state --import --report
