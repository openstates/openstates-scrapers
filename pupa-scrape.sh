#!/bin/bash

set -e

#PUPA_ENV=~/.virtualenvs/pupa
#BILLY_ENV=~/.virtualenvs/openstates

# copy use shift to get rid of first param, pass rest to pupa update
state=$1
shift

# The gentleman's delivery/deployment hehe
#
# NOTE: noop the git pull call in case it fails
# @see https://stackoverflow.com/a/40650331/1858091
( cd /opt/openstates/openstates && \
  git stash && \
  ( git pull origin scratch-pupa-google-pubsub-output || : ) )

export PYTHONPATH=./openstates

$PUPA_ENV/bin/pupa ${PUPA_ARGS:-} update $state "$@"

if [ "$SKIP_BILLY" = true ]; then
  exit 0
fi

export PUPA_DATA_DIR='../openstates/_data'
export PYTHONPATH=./billy_metadata/
$BILLY_ENV/bin/python -m pupa2billy.run $state
$BILLY_ENV/bin/billy-update $state --import --report
