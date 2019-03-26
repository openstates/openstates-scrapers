#!/bin/sh

set -e

# copy use shift to get rid of first param, pass rest to pupa update
state=$1
shift

export PYTHONPATH=./openstates

$PUPA_ENV/bin/pupa ${PUPA_ARGS:-} update $state "$@"
